#!/usr/bin/python3

# Kubernetes SDK
from kubernetes import client as k8sclient, config as k8sconfig
# AWS SDK
import boto3
import botocore

import yaml
import sys
import argparse
import asyncio
import logging

def splitWithEscape(stringToSplit, splitChar, max=None):
    retVal = []
    i = 0
    current = ""
    
    if len(splitChar) != 1:
        raise Exception("Can only split on a single character!")
    
    if max is not None and max <= 0:
        raise Exception("max cannot be less than 0!")

    while i < len(stringToSplit):
        if stringToSplit[i] == '\\' and i < len(stringToSplit) - 1 and stringToSplit[i + 1] == splitChar:
            current += stringToSplit[i+1]
            i += 2
        elif stringToSplit[i] == splitChar:
            retVal.append(current)

            if max is not None and len(retVal)  == max:
                retVal.append(stringToSplit[i + 1:])
                return retVal

            current = ""
            i += 1
        else:
            current += stringToSplit[i]
            i += 1

    retVal.append(current)

    return retVal

def isARN(username):
    return username.startswith("arn:aws:iam")


class MapUser:
    def __init__(self, username, userarn, groups):
        self.username = username
        self.userarn = userarn
        self.groups = list(set(groups))
    
    def add_groups(self, mapUser):
        if self.username != mapUser.username or self.userarn != mapUser.userarn:
            raise Exception("Cannot combine users - userarn and/or usernames don't match")
        self.groups = list(set(self.groups))
        self.groups.extend(mapUser.groups)
    
    def to_dict(self):
        return {
            "username": self.username,
            "userarn": self.userarn,
            "groups": self.groups
        }

class ProgramArgs:
    # _iam_mappings: dict<string, list<string>>
    # _users_to_preserve: list<string>
    # _user_arns_to_preserve: list<string>
    # _ignore_missing_groups: boolean

    def __init__(self):
        self._iam_mappings = {}
        self._users_to_preserve = []
        self._user_arns_to_preserve = []

        # Use ArgParse library to parse arguments
        parser = argparse.ArgumentParser(description="IAM group mappings", add_help=True, allow_abbrev=True, prefix_chars='-')
        mappingHelp = "IAM group mappings should be in the format <IAM Group>=<Kubernetes Group>,<Kubernetes Group>,<Kubernetes group>"
        parser.add_argument("--map", "-map", "-m", action='append', nargs='+', help=mappingHelp)
        preserveHelp = "IAM users to preserve. Supports both names and ARNs, and both commas and separate arguments."
        parser.add_argument("--preserve", "-preserve", "-p", action='append', nargs='+', help=preserveHelp)
        parser.add_argument("--ignore", "-i", action='store_true', help="Ignore any IAM groups that do not exist.")
        args = parser.parse_args()

        self._ignore_missing_groups = args.ignore is not None and args.ignore

        # Parse IAM group mappings <IAM Group>=<Kubernetes Group>,<Kubernetes Group>,<Kubernetes Group>,<Kubernetes Group>
        if args.map is None or len(args.map) == 0:
            raise Exception("Invalid arguments - missing IAM user mappings")

        for mapping in args.map:
            if type(mapping) is list:
                mapping = mapping[0]
            
            try:
                (iamGroup, k8sGroups) = splitWithEscape(mapping, '=', 1)
            except ValueError:
                raise Exception(f"Invalid mapping argument: {mapping}")
            
            if len(iamGroup) == 0:
                raise Exception(f"Invalid mapping argument \"{mapping}\": IAM group cannot be empty!")
            elif iamGroup in self._iam_mappings:
                raise Exception(f"Duplicate mapping for IAM group: {iamGroup}")
            
            k8sGroups = list(set(filter(bool, splitWithEscape(k8sGroups, ','))))
            if len(k8sGroups) == 0:
                logging.warning(f"No kubernetes groups were provided for IAM group: {iamGroup}")

            k8sGroups = list(set(filter(bool, k8sGroups)))
            if len(k8sGroups) == 0:
                logging.warning(f"No kubernetes groups were provided for IAM group: {iamGroup}")
                continue
            self._iam_mappings[iamGroup] = k8sGroups
        
        if len(self._iam_mappings) == 0:
            raise Exception("Invalid arguments - missing IAM user mappings")

        # Parse users to preserve
        if args.preserve is None:
            args.preserve = []

        for usersToPreserve in args.preserve:
            if type(usersToPreserve) is list:
                usersToPreserve = usersToPreserve[0]

            split = splitWithEscape(usersToPreserve, ',')

            if len(split) == 0:
                logging.warning("Empty preserve argument")
            
            for userToPreserve in split:
                if isARN(userToPreserve):
                    self._user_arns_to_preserve.append(userToPreserve)
                else:
                    self._users_to_preserve.append(userToPreserve)
        
        # Get distinct and non-empty users
        self._users_to_preserve = list(set(filter(bool, self._users_to_preserve)))
        self._user_arns_to_preserve = list(set(filter(bool, self._user_arns_to_preserve)))
    
    def get_iam_groups(self):
        return self._iam_mappings.keys()
    
    def get_kubernetes_groups(self, iamGroup):
        if iamGroup not in self._iam_mappings:
            raise KeyError(f"Group not found: {iamGroup}")
        return self._iam_mappings[iamGroup]
    
    def is_preserve_user(self, iamUser):
        if isARN(iamUser):
            return iamUser in self._user_arns_to_preserve
        else:
            return iamUser in self._users_to_preserve
    
    def is_ignore_missing_groups(self):
        return self._ignore_missing_groups

class AwsIamClient:
    def __init__(self, args):
        self._args = args
        self._aws_client = boto3.client('iam')

    async def get_users(self):
        groups = self._args.get_iam_groups()
        
        # Asynchronously get all IAM users for the given groups
        mappedUsersOfGroups = await asyncio.gather(*[self.get_iam_users_in_group(g) for g in groups])
        
        # Flat map IAM users
        users = {}
        for groupUsers in mappedUsersOfGroups:
            for user in groupUsers:
                if user.username in users.keys():
                    users[user.username].add_groups(user)
                else:
                    users[user.username] = user
        
        # Remove preserved users
        users = filter(lambda u: not self._args.is_preserve_user(u.username) and not self._args.is_preserve_user(u.userarn), users.values())
        
        # Convert MapUser objects to dicts
        return list(u.to_dict() for u in users)
    
    async def get_iam_users_in_group(self, iamGroup):
        """
        Asynchronously get all IAM users in `iamGroup`
        """
        try:
            kubernetesGroups = self._args.get_kubernetes_groups(iamGroup)
            mapFn = lambda user: MapUser(user["UserName"], user["Arn"], list(kubernetesGroups))
            maxItems = 100
            response = self._aws_client.get_group(GroupName = iamGroup, MaxItems = maxItems)
            mappedUsers = list(map(mapFn, response["Users"]))
            numCalls = 1
            
            # If response is truncated, continue making calls with the previous marker
            while response["IsTruncated"]:
                marker = response["Marker"]
                response = self._aws_client.get_group(GroupName = iamGroup, Marker = marker, MaxItems = maxItems)
                mappedUsers.extend(list(map(mapFn, response["Users"])))
                numCalls += 1
        
            logging.info(f"Received {len(mappedUsers)} IAM users from group {iamGroup} ({numCalls} API calls)")

            return mappedUsers
        except self._aws_client.exceptions.NoSuchEntityException:
            if self._args.is_ignore_missing_groups():
                logging.warning(f"IAM group {iamGroup} does not exist!")
                return []
            else:
                exec_type, exec_value, exec_traceback = sys.exc_info()
                logging.error(f"Received exception type {exec_type} with value {exec_value} when getting IAM group {iamGroup}:\n{exec_traceback}")
                raise Exception(f"IAM group {iamGroup} does not exist!")
        except Exception:
            exec_type, exec_value, exec_traceback = sys.exc_info()
            logging.error(f"Received exception type {exec_type} with value {exec_value} when getting IAM group {iamGroup}:\n{exec_traceback}")
            raise Exception(f"Error getting IAM group {iamGroup}: {exec_value}")

async def main():
    logging.basicConfig(format='[%(levelname)s] %(asctime)s: %(message)s', level='INFO')
    
    logging.info("Starting eks-map-iam-groups")

    args = ProgramArgs()
    users = await AwsIamClient(args).get_users()

    namespace = "kube-system"
    configmap = "aws-auth"
    
    try:
        k8sconfig.load_incluster_config()
    except k8sconfig.config_exception.ConfigException:
        exec_type, exec_value, exec_traceback = sys.exc_info()
        logging.warning(f"Received exception type {exec_type} with value {exec_value} when getting in-cluster Kubernetes config. Attempting to load ~/.kube config")
        try:
          k8sconfig.load_kube_config()
        except k8sconfig.config_exception.ConfigException:
            exec_type, exec_value, exec_traceback = sys.exc_info()
            logging.error(f"Received exception type {exec_type} with value {exec_value} when loading ~/.kube config")
    
    k8sv1 = k8sclient.CoreV1Api()

    # type = V1ConfigMap
    aws_auth = None
    try:
        aws_auth = k8sv1.read_namespaced_config_map(name=configmap, namespace=namespace)
    except Exception:
        exec_type, exec_value, exec_traceback = sys.exc_info()
        raise Exception(f"Received exception type {exec_type} with value {exec_value} when getting ConfigMap {namespace}/{configmap}:\n{exec_traceback}")
    aws_auth_data = aws_auth.data
    
    preexisting_aws_auth_users = aws_auth_data["mapUsers"]
    aws_auth_users = []
    if aws_auth_users is not None:
        logging.info(f"Pre-existing user map:\n{preexisting_aws_auth_users}")
        aws_auth_users = yaml.safe_load(preexisting_aws_auth_users)
        aws_auth_users = list(filter(lambda u: args.is_preserve_user(u["username"]) or args.is_preserve_user(u["userarn"]), aws_auth_users))
    aws_auth_users.extend(users)
    aws_auth_users.sort(key = lambda u: u["username"])
    aws_auth_users_yaml = yaml.dump(aws_auth_users)

    if preexisting_aws_auth_users == aws_auth_users_yaml:
        logging.info(f"Not updating ConfigMap {namespace}/{configmap} - no changes to make")
    else:
        logging.info(f"Final user map:\n{aws_auth_users_yaml}")
        aws_auth_data["mapUsers"] = aws_auth_users_yaml
        aws_auth.data = aws_auth_data
        try:
            k8sv1.replace_namespaced_config_map(name=configmap, namespace=namespace, body=aws_auth, pretty=True)
        except:
            exec_type, exec_value, exec_traceback = sys.exc_info()
            raise Exception(f"Received exception type {exec_type} with value {exec_value} when updating ConfigMap {namespace}/{configmap}:\n{exec_traceback}")

asyncio.run(main())
