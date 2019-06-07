#!/usr/bin/python3

# Kubernetes SDK
from kubernetes import client,config
# AWS SDK
import boto3
import botocore
import yaml
import collections # TODO Remove
import types # TODO Remove
import sys
import argparse
import json # TODO Remove
import asyncio
import traceback # TODO Remove

# TODO Add comments

class MapUser:
    def __init__(self, username, rolearn, groups):
        self.username = username
        self.rolearn = rolearn
        self.groups = list(set(groups))
    
    def add_groups(self, mapUser):
        if self.username != mapUser.username or self.rolearn != mapUser.rolearn:
            raise Exception("Cannot combine users - rolearn and/or usernames don't match")
        self.groups.extend(mapUser.groups)
        self.groups = list(set(self.groups))

class ProgramArgs:
    # __iam_mappings__: dict<string, list<string>>
    # __users_to_preserve__: list<string>

    def __init__(self):
        self.__iam_mappings__ = {}
        self.__users_to_preserve__ = []

        parser = argparse.ArgumentParser(description="IAM group mappings", add_help=True, allow_abbrev=True, prefix_chars='-')
    
        mappingHelp = "IAM group mappings should be in the format <IAM Group>=<Kubernetes Group>,<Kubernetes Group>,<Kubernetes group>"
        parser.add_argument("--map", "-map", "-m", action='append', nargs='+', help=mappingHelp)
        preserveHelp = "IAM users to preserve. Supports both names and ARNs, and both commas and separate arguments."
        parser.add_argument("--preserve", "-preserve", "-p", action='append', nargs='+', help=preserveHelp)
        parser.add_argument("--ignore", "-i", action='store_true', help="Ignore any IAM groups that do not exist.")
    
        args = parser.parse_args()

        self.__ignore_missing_groups__ = args.ignore is not None and args.ignore

        print("YAML Mapping of args:") # TODO remove
        print("---") # TODO remove
        yaml.dump(args, sys.stdout) # TODO remove
        print("---") # TODO remove
        
        # Parse IAM group mappings
        if args.map is None or len(args.map) == 0:
            raise Exception("Invalid arguments - missing IAM user mappings")

        for mapping in args.map:
            if type(mapping) is list:
                mapping = mapping[0]

            print("mapping is %s" % type(mapping)) # TODO remove

            split = mapping.split("=")
            if(len(split) != 2):
                raise Exception("Invalid mapping argument: %s" % mapping)
            
            iam_group = split[0]
            k8s_groups = split[-1].split(",")

            if len(split) == 0:
                raise Exception("Invalid mapping argument - missing Kubernetes groups for IAM group: %s" % iam_group)
            
            if iam_group in self.__iam_mappings__:
                raise Exception("Duplicate mapping for IAM group: %s" % iam_group)
            
            k8s_groups = list(set(filter(bool, k8s_groups)))
            if len(k8s_groups) == 0:
                print("No kubernetes groups were provided for IAM group: %s" % iam_group)
                continue
            self.__iam_mappings__[iam_group] = k8s_groups
        
        # Parse users to preserve
        if(args.preserve is None):
            args.preserve = []

        for usersToPreserve in args.preserve:
            if type(usersToPreserve) is list:
                usersToPreserve = usersToPreserve[0]

            print("usersToPreserve is %s" % type(mapping)) # TODO remove

            split = usersToPreserve.split(",")

            if len(split) == 0:
                print("Warning: empty preserve argument")
            
            for userToPreserve in split:
                if userToPreserve.startswith("arn:aws:iam"):
                    userSplit = userToPreserve.split('/')
                    if len(userSplit) != 2:
                        raise Exception("Invalid IAM user ARN in preserve argument: %s" % userToPreserve)
                    userToPreserve = userSplit[-1]

                self.__users_to_preserve__.append(userToPreserve)
            
        print("IAM mappings: %s" % json.dumps(self.__iam_mappings__)) # TODO remove

        self.__users_to_preserve__ = list(set(filter(bool, self.__users_to_preserve__)))

        print("Users to preserve: %s" % json.dumps(self.__users_to_preserve__)) # TODO remove

    def get_all_mappings(self):
        return self.__iam_mappings__
    
    def get_iam_groups(self):
        return self.__iam_mappings__.keys()
    
    def get_kubernetes_groups(self, iamGroup):
        if(iamGroup not in self.__iam_mappings__):
            raise KeyError("Group not found: %s" % iamGroup)
        return self.__iam_mappings__[iamGroup]
    
    def is_preserve_user(self, iamUser):
        if(iamUser.startswith("arn:aws:iam")):
            split = iamUser.split('/')

            if(len(split) != 2):
                raise Exception("Invalid IAM user ARN: %s" % iamUser)
            
            iamUser = split[-1]
        return iamUser in self.__users_to_preserve__
    
    def is_ignore_missing_groups(self):
        return self.__ignore_missing_groups__

class AWSIAMClient:
    def __init__(self, args):
        self.__args__ = args

        self.__aws_client__ = boto3.client('iam')


    async def get_users(self):
        print("get_users") # TODO remove
        
        groups = self.__args__.get_iam_groups()
        
        mappedUsersOfGroups = await asyncio.gather(*[self.get_iam_users_in_group(g) for g in groups])

        print("Users: %s" % yaml.dump(mappedUsersOfGroups)) # TODO remove

        users = {}
        for groupUsers in mappedUsersOfGroups:
            for user in groupUsers:
                if user.username in users:
                    existingUser = users[user.username].add_groups(user)
                    users[user.username] = existingUser
                else:
                    users[user.username] = user
        
        # TODO handle users to preserve

        return list(users.values())
    
    async def get_iam_users_in_group(self, iamGroup):
        try:
            kubernetesGroups = self.__args__.get_kubernetes_groups(iamGroup)
            mappedUsers = []
            mapFn = lambda user: MapUser(user["UserName"], user["Arn"], list(kubernetesGroups))
            maxItems = 100 # TODO test
            print("Getting IAM users from group %s" % iamGroup) # TODO remove
            response = self.__aws_client__.get_group(GroupName = iamGroup, MaxItems = maxItems)
            print("IAM response for group %s: %s" % (iamGroup, yaml.dump(response))) # TODO remove
            mappedUsers.extend(list(map(mapFn, response["Users"])))

            while(response["IsTruncated"]):
                marker = response["Marker"]
                response = self.__aws_client__.get_group(GroupName = iamGroup, Marker = marker, MaxItems = maxItems)
                mappedUsers.extend(list(map(mapFn, response["Users"])))
        
            print("Received %d IAM users from group %s" % (len(mappedUsers), iamGroup))

            return mappedUsers
        except Exception:
            exec_type, exec_value, exec_traceback = sys.exc_info()
            print("Received exception type %s with value %s when getting IAM group %s" % (exec_type, exec_value, iamGroup)) # TODO remove
            if self.__args__.is_ignore_missing_groups():
                print("Warning: IAM group %s does not exist!" % iamGroup)
            else:
                raise Exception("IAM group %s does not exist!" % iamGroup)

    

def get_iam_users(group):
    print("TODO")

async def main():
    args = ProgramArgs()
    users = await AWSIAMClient(args).get_users()
    print("Mapped Users: %s" % yaml.dump(users)) # TODO remove

    # TODO kubernetes update
    

asyncio.run(main())
