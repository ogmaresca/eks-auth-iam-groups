#!/bin/bash

_passback() { while [ 0 -lt $# ]; do printf '%q=%q;' "$1" "${!1}"; shift; done; }

# https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html

AWS_ACCOUNT_NUM=$(aws sts get-caller-identity --output text --query 'Account')

if [ -z $AWS_ACCOUNT_NUM ]
then
  echo -e "Could not retrieve AWS account number"
  exit 1
fi

USER_YAML='[]'

shopt -s expand_aliases
alias yaml-value="yq -e -r"
alias yaml="yq -e -r --yaml-output"

MAPPING_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]
do
  key="$1"
  
  case $key in
    --map=*)
    MAPPING_ARGS+=("${1#--map=}")
    shift
    ;;
    
    --map|-map)
    MAPPING_ARGS+=("$2")
    shift
    shift
    ;;
    
    *)    # unknown option
    echo -e "Unknown argument $1"
    exit 1
    ;;
  esac
done

# Validate number of arguments
if [[ ${#MAPPING_ARGS[@]} -eq 0 ]]
then
  echo -e "Missing group mappings"
  exit 1
fi

# Parse arguments
declare -A MAPPINGS
for ARG in ${MAPPING_ARGS[@]}
do
  IFS='=' read -r -a SPLIT_ARG <<< $ARG
  
  # Validate argument is in format a=b
  if [[ ${#SPLIT_ARG[@]} -ne 2 ]]
  then
    echo -e ${#SPLIT_ARG[@]}
    echo -e "Invalid mapping argument format: $ARG"
    exit 1
  fi
  
  IAM_GROUP=${SPLIT_ARG[0]}
  if [ -z $IAM_GROUP ]
  then
    echo -e "Missing IAM group in mapping argument: $ARG"
    exit 1
  fi
  
  K8S_GROUPS_STR=${SPLIT_ARG[1]}
  if [ -z $K8S_GROUPS_STR ]
  then
    echo -e "Missing kubernetes groups in mapping argument: $ARG"
    exit 1
  fi
  
  IFS=',' read -r -a K8S_GROUPS <<< $K8S_GROUPS_STR
  
  MAPPINGS+=( [${IAM_GROUP}]=${K8S_GROUPS} )
done

for IAM_GROUP in ${!MAPPINGS[@]}
do
  K8S_GROUPS=${MAPPINGS[${IAM_GROUP}]}
  echo "Adding IAM group ${IAM_GROUP} to Kubernetes roles: ${K8S_GROUPS[@]}"
  
  # TODO use AWS CLI to get values
  IAM_USERS=('user1' 'user2' 'user3' "${IAM_GROUP}user4")
  
  for IAM_USER in ${IAM_USERS[@]}
  do
    # Get the index of the YAML array that the user is in
    INDEX=$(echo "$USER_YAML" | yaml-value --arg iamUsername $IAM_USER 'to_entries | .[] | select(.value.username == $iamUsername) | .key');
    if [ -z $INDEX ]
    then
      USER_YAML=$(echo "$USER_YAML" | yaml --arg iamUser $IAM_USER --arg roleArn "arn:aws:iam::${AWS_ACCOUNT_NUM}:user/${IAM_USER}" '. += [{ groups: [], rolearn: $roleArn, username: $iamUser }]')
      
      ARR_LENGTH=$(echo "$USER_YAML" | yaml-value 'length')
      INDEX=$(($ARR_LENGTH - 1))
      
      for K8S_GROUP in ${K8S_GROUPS[@]}
      do
        if [ -z $(echo "$USER_YAML" | yaml-value --argjson index $INDEX --arg group $K8S_GROUP '.[$index].groups | select(. == $group)') ]
        then
          USER_YAML=$(echo "$USER_YAML" | yaml-value --argjson index $INDEX --arg group $K8S_GROUP '.[$index].groups += [$group]')
        fi
      done
    fi
  done
  
  unset K8S_GROUPS
done

echo "$USER_YAML"
