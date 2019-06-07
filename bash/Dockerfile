FROM ubuntu:18.04

# Install Python, Pip, and jq
RUN apt-get update \
 && apt-get install -y --install-recommends \
      python3 \
      python3-pip \
      less \
      jq \
 && pip3 install --upgrade pip
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && rm -rf /etc/apt/sources.list.d/*

# Install AWS CLI
RUN pip3 --no-cache-dir install awscli

# Install yq
RUN pip3 --no-cache-dir install yq

# Install kubectl
ENV KUBECTL_VERSION=v1.14.2
RUN curl -L -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl
RUN chmod +x /usr/local/bin/kubectl

# Add script
COPY eks-map-iam-groups.sh /usr/bin/eks-map-iam-groups.sh
RUN chmod +x /usr/bin/eks-map-iam-groups.sh

WORKDIR /work

ENTRYPOINT ["eks-map-iam-groups.sh"]
CMD []
