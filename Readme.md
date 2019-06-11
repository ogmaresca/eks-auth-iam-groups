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
helm upgrade --install --namespace=kube-system eks-auth-iam-groups eks-auth-iam-groups/eks-auth-iam-groups --set 'mappings.<IAM Group to map>={system:masters}'
```

To preserve users, add the following arguments:

``` bash
--set 'preserve={<iam_user_1>,<iam_user_2>}'
```

To fail on non-existent IAM groups, add the following arguments:

``` bash
--set ignoreMissingIAMGroups=false
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

IAM group ARNs are not supported.

## Preserving users

If you want to manually control some users, you can add them as a preserve argument to ignore them. These users will not be added by this job, and if they already exist in the `aws-auth` configmap then they will not be updated or deleted. Both usernames and ARNs are supported.

* `--preserve=<iam_user>`

## Ignore Unknown IAM Groups

By default, this program will fail if one of the IAM groups doesn't exist. Adding the argument `--ignore` will prevent this.

# Helm Chart Configuration

By default `eks-auth-iam-groups` will run every minute, and fail because of a lack of IAM group mappings and IAM access.

| Parameter                    | Description                                                                   | Default                      |
| ---------------------------- | ----------------------------------------------------------------------------- | ---------------------------- |
| `schedule`                   | The Cron Tab schedule to run.                                                 | `* * * * *`                  |
| `startingDeadlineSeconds`    | How long after a missed schedule to retry until it's counted as a failed run. | 600                          |
| `successfulJobsHistoryLimit` | How many successful job pods to keep.                                         | 1                            |
| `suspend`                    | Whether the job should be suspended.                                          | `false`                      |
| `concurrencyPolicy`          | Whether two or more jobs can be ran simultaneously.                           | Forbid                       |
| `failedJobsHistoryLimit`     | How many failed job pods to keep.                                             | 3                            |
| `backoffLimit`               | How many times to retry the pod until the job is considered failed.           | 1                            |
| `mappings`                   | The IAM to Kubernetes group mappings.                                         | `{}`                         |
| `preserve`                   | The IAM users to preserve.                                                    | `[]`                         |
| `ignoreMissingIAMGroups`     | Whether to ignore non-existent IAM groups provided in `mappings`.             | `true`                       |
| `image.repository`           | The Docker Hub repository.                                                    | gmaresca/eks-auth-iam-groups |
| `image.tag`                  | The image tag.                                                                | latest                       |
| `pullPolicy`                 | The image pull policy.                                                        | IfNotPresent                 |
| `imagePullSecrets`           | Image Pull Secrets to use.                                                    | `[]`                         |
| `nameOverride`               | An override value for the name.                                               | ``                           |
| `fullnameOverride`           | An override value for the full name.                                          | ``                           |
| `cronjobLabels`              | Labels to add to the CronJob.                                                 | `{}`                         |
| `cronjobAnnotations`         | Annotations to add to the CronJob.                                            | `{}`                         |
| `jobLabels`                  | Labels to add to the Jobs.                                                    | `{}`                         |
| `jobAnnotations`             | Annotations to add to the Jobs,                                               | `{}`                         |
| `podLabels`                  | Labels to add to the Pods,                                                    | `{}`                         |
| `podAnnotations`             | Annotations to add to the Pods,                                               | `{}`                         |
| `aws.region`                 | The AWS region to use.                                                        | `null`                       |
| `aws.accessKey`              | The AWS access key to use.                                                    | `null`                       |
| `aws.secretKey`              | The AWS secret key to use.                                                    | `null`                       |
| `aws.profile`                | The AWS profile to use.                                                       | default                      |
| `aws.volume`                 | The fields to add to the volume for mounting AWS credentials.                 | `{}`                         |
| `aws.volume.enabled`         | Whether to mount the AWS credentials. All volume fields needs to be provided. | `false`                      |
| `aws.subPath`                | The subpath in the volume to the location of the AWS credentials.             | ``                           |
| `resources.requests.cpu`     | The CPU requests.                                                             | `null`                       |
| `resources.requests.memory`  | The memory requests.                                                          | `null`                       |
| `resources.limits.cpu`       | The CPU limits.                                                               | `null`                       |
| `resources.limits.memory`    | The memory limits.                                                            | `null`                       |
| `nodeSelector`               | The pod node selector.                                                        | `{}`                         |
| `tolerations`                | The pod node tolerations.                                                     | `{}`                         |
| `affinity`                   | The pod node affinity.                                                        | `{}`                         |
| `securityContext`            | The pod security context.                                                     | `{}`                         |
| `hostNetwork`                | Whether to use the host network of the node.                                  | `false`                      |
| `initContainers`             | Init containers to add.                                                       | `[]`                         |
| `sidecars`                   | Additional containers to add.                                                 | `[]`                         |


# Docker Hub

[View the Docker Hub page for this repo](https://hub.docker.com/r/gmaresca/eks-auth-iam-groups)
