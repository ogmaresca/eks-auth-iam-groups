# eks-auth-iam-groups

Inspired by [iam-eks-user-mapper](https://github.com/ygrene/iam-eks-user-mapper). This project aims to allow mapping multiple groups in the auth map, as well as control the polling rate.

# Arguments

## IAM Group Mapping

* `--map=<group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`
* `--map <group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`
* `-map <group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`

These are all valid.

## Preserving users

If you want to manually control some users, you can add them as a preserve argument to ignore them. These users will not be added by this job, and if they already exist in the `aws-auth` configmap then they will not be updated or deleted.

* `--preserve=<group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`
* `--preserve <group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`
* `-preserve <group>=<kubernetes_role>,<kubernetes_role>,<kubernetes_role>`

# TODO

* Document arguments
* Document Kubernetes installation
