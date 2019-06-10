# eks-auth-iam-groups

Inspired by [iam-eks-user-mapper](https://github.com/ygrene/iam-eks-user-mapper). This project aims to allow mapping multiple groups in the auth map, as well as control the scheduling rate.

# Installation

You can use the `IAMReadOnlyAccess` policy to give this app the AWS access it needs. For the most minimal IAM policy, use the following:

``` json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:GetGroup"
            ],
            "Resource": "*"
        }
    ]
}
```

First, add this repo to Helm:

``` bash
helm repo add eks-auth-iam-groups https://raw.githubusercontent.com/ggmaresca/eks-auth-iam-groups/master/charts
helm repo update
```

Then use this command to install it:

``` bash
helm upgrade --install --namespace=kube-system eks-auth-iam-groups eks-auth-iam-groups/eks-auth-iam-groups --set 'groupMappings.<IAM Group to map>={system:masters}'
```

To preserve users, add the following arguments:

``` bash
--set 'preserveUsers={<iam_user_1>,<iam_user_2>}'
```

To fail on non-existent IAM groups, add the following arguments:

``` bash
--set ignoreMissingIAMGroups=true
```

## AWS Credentials

To install using Kube2IAM, add the following arguments:

``` bash
--set 'podAnnotations.iam\.amazonaws\.com/role=<IAM role>'
```

To install with access and secret keys, add the following arguments instead:

``` bash
--set aws.accessKey=<AWS Access Key>,aws.secretKey=<AWS Secret Key>
```

To install in a local cluster using a Volume Mount, add the following arguments instead:

``` bash
--set aws.volume.enabled=true,aws.volume.hostPath.path=${HOME}/.aws
```

To install in a local cluster using a pre-existing Secret that replicates the structure of the `~/.aws` folder from the AWS CLI, add the following arguments instead:

``` bash
--set aws.volume.enabled=true,aws.volume.secret.secretName=<Pre-existing AWS credentials Secret>
```

Any value in the [v1 Volume API spec](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.12/#volume-v1-core) is supported.

# Arguments

## IAM Group Mapping

* `--map=<iam_group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`

These are all valid.

## Preserving users

If you want to manually control some users, you can add them as a preserve argument to ignore them. These users will not be added by this job, and if they already exist in the `aws-auth` configmap then they will not be updated or deleted. Both usernames and ARNs are supported.

* `--preserve=<iam_user>`

## Ignore Unknown IAM Groups

By default, this program will fail if one of the IAM groups doesn't exist. Adding the argument `--ignore` will prevent this.

# Docker Hub

[View the Docker Hub page for this repo](https://hub.docker.com/r/gmaresca/eks-auth-iam-groups)
