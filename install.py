#!/usr/bin/python3

from subprocess import STDOUT, check_call
import os
import sys
import getopt
from time import sleep
import requests
import apt

def main(argv):
    kube_version = ''
    node_type = ''
    try:
      opts, args = getopt.getopt(argv,"hk:n:c:",["kubernetes=", "node-type=", "containerd="])
    except getopt.GetoptError:
      print('-kv <kubernetes version> -nt <node-type>')
      sys.exit(2)
    for opt, arg in opts:
        if opt in ("-k", "--kubernetes"):
            kube_version = arg
        if opt in ("-n", "--node-type"):
            node_type = arg
        if opt in ("-n", "--containerd"):
            containerd_version = arg
    
    print('Upgrading the system...')
    
    check_call(['apt', 'update'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    check_call(['apt', 'upgrade', '-y'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Installing basic tools...')
    
    check_call(['apt', 'install', '-y', 'mc', 'vim', 'mlocate', 'net-tools', 'iputils-ping', 'open-vm-tools', 'ca-certificates', 'curl', 'apt-transport-https'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Setting up the environment...')
    
    check_call(['mkdir', '-pv', '/root/.vim/colors'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    url = 'https://raw.githubusercontent.com/k8stools/ubuntu-install/main/files/bashrc'
    r = requests.get(url, allow_redirects=True)
    open('/root/.bashrc', 'wb').write(r.content)
    
    url = 'https://raw.githubusercontent.com/k8stools/ubuntu-install/main/files/fromthehell.vim'
    r = requests.get(url, allow_redirects=True)
    open('/root/.vim/colors/fromthehell.vim', 'wb').write(r.content)
    
    url = 'https://raw.githubusercontent.com/k8stools/ubuntu-install/main/files/vimrc'
    r = requests.get(url, allow_redirects=True)
    open('/root/.vimrc', 'wb').write(r.content)
    
    # print('Set SSH keys...')

    # with open('/root/.ssh/authorized_keys', 'w') as file_out:
    #     file_out.write('''''')
    
    if (kube_version != ''):
        install_k8s(kube_version, node_type, containerd_version)

def install_k8s(kube_version, node_type, containerd_version):
    
    check_call(['mkdir', '-pv', '/root/tools/'],
        stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Installing Containerd ' + containerd_version + ' ...')
    
    url = "https://github.com/containerd/containerd/releases/download/v" + containerd_version + "/containerd-" + containerd_version + "-linux-amd64.tar.gz"
    r = requests.get(url, allow_redirects=True)
    open('/root/tools/containerd.tar.gz', 'wb').write(r.content)
    check_call(['tar', 'Cxzvf', '/usr/local', '/root/tools/containerd.tar.gz'],
        stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    runc_version = "1.1.4"
    
    print('Installing runc ' + runc_version + ' ...')
    
    url = "https://github.com/opencontainers/runc/releases/download/v" + runc_version + "/runc.amd64"
    r = requests.get(url, allow_redirects=True)
    open('/root/tools/runc.amd64', 'wb').write(r.content)
    check_call(['install', '-m', '755', '/root/tools/runc.amd64', '/usr/local/sbin/runc'],
        stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    cni_plugins_version = "1.1.1"
    
    print('Installing cni plugins ' + cni_plugins_version + ' ...')
    
    url = "https://github.com/containernetworking/plugins/releases/download/v" + cni_plugins_version + "/cni-plugins-linux-amd64-v" + cni_plugins_version + ".tgz"
    r = requests.get(url, allow_redirects=True)
    open('/root/tools/cni-plugins.tgz', 'wb').write(r.content)
    check_call(['mkdir', '-p', '/opt/cni/bin'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    check_call(['tar', 'Cxzvf', '/opt/cni/bin', '/root/tools/cni-plugins.tgz'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Configuring Containerd ...')
    
    check_call(['mkdir', '-p', '/etc/containerd'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    check_call(['containerd', 'config', 'default'], stdout=open('/etc/containerd/config.toml','wb'), stderr=STDOUT)
    check_call(["sed -i 's/SystemdCgroup \= false/SystemdCgroup \= true/g' /etc/containerd/config.toml"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    
    print('Configuring Systemd daemon ...')
    url = "https://raw.githubusercontent.com/containerd/containerd/main/containerd.service"
    r = requests.get(url, allow_redirects=True)
    open('/etc/systemd/system/containerd.service', 'wb').write(r.content)
    check_call(['systemctl', 'daemon-reload'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    check_call(['systemctl', 'enable', '--now', 'containerd'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Installing Kubernetes ' + kube_version + ' ...')
    check_call(["sed -i 's/swap.img/# swap.img/g' /etc/fstab"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    check_call(["swapoff -a"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    with open('/etc/sysctl.d/kubernetes.conf', 'w') as file_out:
        file_out.write('''net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1''')
    check_call(["modprobe overlay"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    check_call(["modprobe br_netfilter"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    check_call(["sysctl --system"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    url = "https://packages.cloud.google.com/apt/doc/apt-key.gpg"
    r = requests.get(url, allow_redirects=True)
    open('/usr/share/keyrings/kubernetes-archive-keyring.gpg', 'wb').write(r.content)
    with open('/etc/apt/sources.list.d/kubernetes.list', 'w') as file_out:
        file_out.write("deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main\n")
    check_call(["apt update"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    check_call(["apt install -y kubelet=" + kube_version + "-00 kubeadm=" + kube_version + "-00 kubectl=" + kube_version + "-00"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
    check_call(['apt-mark', 'hold', 'kubeadm', 'kubectl', 'kubelet'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    join_command = ''
    
    if node_type == "controller":
        print('Initializing controller node ...')
        check_call(["kubeadm init --pod-network-cidr=10.244.0.0/16"], stdout=open('/root/tools/k8s_init_out','wb'), stderr=STDOUT, shell=True)
        check_call(["mkdir -p $HOME/.kube"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(["cp -i /etc/kubernetes/admin.conf $HOME/.kube/config"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(["chown $(id -u):$(id -g) $HOME/.kube/config"], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        
        with open('/root/tools/k8s_init_out', 'r') as k8s_init_out:
            for line in k8s_init_out.readlines():
                if '--token' in line:
                    join_command = line[:-2]
                if '--discovery-token-ca-cert-hash' in line:
                    join_command = join_command + line[1:-1]
                    break
                
    
    print('Removing downloaded tools ...')
    check_call(['rm', '-rf', '/root/tools'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Use the following command to join worker nodes to this cluster:')
    print(join_command)
    print()
    print('To join Windows node with ContainerD don\'t forget to add --cri-socket "npipe:////./pipe/containerd-containerd"')
    print(join_command + '--cri-socket "npipe:////./pipe/containerd-containerd"')
    
    # print('Reboot ...')
    # os.system('reboot')

if __name__ == "__main__":
    main(sys.argv[1:])