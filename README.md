# Ubuntu 22.04 K8S installer with ContainerD

The install.py script is a very basic one.  
This script sets up the vim color to fromthehell (https://github.com/szorfein/fromthehell.vim)  
It tested on Ubuntu 22.04 server.

For now the script has to be runned by root user.  
It downloads and create files in the /root/ directory

You don't need to clone the repository to use the script.  
The bashrc and vim files are dowloaded from the repo by the script.

## Usage:

For controller node run the script like:

```
./install.py --kubernetes=KUBERNETES_VERSION --containerd=CONTAINERD_VERSION --node-type=controller
```

Example:

```
./install.py --kubernetes=1.24.6 --containerd=1.6.8 --node-type=controller
```

For worker node:

```
./install.py --kubernetes=KUBERNETES_VERSION --containerd=CONTAINERD_VERSION --node-type=worker --join-token=TOKEN_FROM_JOIN_COMMAND --discovery-token=DISCOVERY_TOKEN_FROM_JOIN_COMMAND --controller-node=CONTROLLER_NODE_IP
```

Example:

```
./install.py --kubernetes=1.24.6 --containerd=1.6.8 --node-type=worker --join-token=7yqefg.7djpmf6shjvu2wfm --discovery-token=f00ca89badcd4b88c3ece7d0e7a77c38075ed4952d80373e98b1f67639e262cc --controller-node=10.172.0.100
```
