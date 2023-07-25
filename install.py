#!/usr/bin/python3

from subprocess import STDOUT, check_call
import os
import sys
import getopt
from time import sleep
import requests
import apt
import subprocess

def main(argv):
    kube_version = ''
    node_type = ''
    
    try:
      opts, args = getopt.getopt(argv,"hk:n:c:t:d:m:",["kubernetes=", "node-type=", "containerd=", "join-token=", "discovery-token=", "controller-node="])
    except getopt.GetoptError:
      print('-k <kubernetes version> -n <node-type>')
      sys.exit(2)
    for opt, arg in opts:
        if opt in ("-k", "--kubernetes"):
            kube_version = arg
        if opt in ("-n", "--node-type"):
            node_type = arg
        if opt in ("-c", "--containerd"):
            containerd_version = arg
        if opt in ("-t", "--join-token"):
            join_token = arg
        if opt in ("-d", "--discovery-token"):
            discovery_token = arg
        if opt in ("-m", "--controller-node"):
            controller_node = arg
    
    print('Upgrading the system...')
    
    check_call(['apt', 'update'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    check_call(['apt', 'upgrade', '-y'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Installing basic tools...')
    
    check_call(['apt', 'install', '-y', 'mc', 'curl', 'vim', 'mlocate', 'net-tools', 'iputils-ping', 'ca-certificates', 'curl', 'apt-transport-https', 'bashtop', 'qemu-guest-agent'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    check_call(['systemctl', 'enable', 'qemu-guest-agent'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
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
        if (node_type == ''):
            print('Please select node type. (--node-type=[controller, worker]')
            sys.exit()
        if(node_type == 'controller'):
            install_k8s(kube_version, node_type, containerd_version)
        elif(node_type == 'worker'):
            install_k8s(kube_version, node_type, containerd_version, controller_node, join_token, discovery_token)
        else:
            print('Please select proper node type. (--node-type=[controller, worker]')
            sys.exit(2)

def download_and_dearmor(url, output_path):
    try:
        # Download the GPG key file using requests
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save the downloaded GPG key file to the specified output path
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Execute the gpg --dearmor command using subprocess
        subprocess.run(['gpg', '--dearmor', '-o', '/etc/apt/keyrings/kubernetes-archive-keyring.gpg', output_path], check=True)

        print("GPG key downloaded and processed successfully.")
    except Exception as e:
        print("Error: ", e)

def install_k8s(kube_version, node_type, containerd_version, controller_node='', join_token='', discovery_token=''):
    
    check_call(['mkdir', '-pv', '/root/tools/'],
        stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    print('Installing Containerd ' + containerd_version + ' ...')
    
    url = "https://github.com/containerd/containerd/releases/download/v" + containerd_version + "/containerd-" + containerd_version + "-linux-amd64.tar.gz"
    r = requests.get(url, allow_redirects=True)
    open('/root/tools/containerd.tar.gz', 'wb').write(r.content)
    check_call(['tar', 'Cxzvf', '/usr/local', '/root/tools/containerd.tar.gz'],
        stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    runc_version = "1.1.8"
    
    print('Installing runc ' + runc_version + ' ...')
    
    url = "https://github.com/opencontainers/runc/releases/download/v" + runc_version + "/runc.amd64"
    r = requests.get(url, allow_redirects=True)
    open('/root/tools/runc.amd64', 'wb').write(r.content)
    check_call(['install', '-m', '755', '/root/tools/runc.amd64', '/usr/local/sbin/runc'],
        stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    cni_plugins_version = "1.3.0"
    
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
    
    gpg_key_url = "https://packages.cloud.google.com/apt/doc/apt-key.gpg"
    output_file_path = "/usr/share/keyrings/kubernetes-archive-keyring.gpg"
    download_and_dearmor(gpg_key_url, output_file_path)

    with open('/etc/apt/sources.list.d/kubernetes.list', 'w') as file_out:
        file_out.write("deb [signed-by=/etc/apt/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main\n")
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
        
        print("Installing Calico networking tools ...")
    
        check_call(['curl -L https://github.com/projectcalico/calico/releases/download/v3.26.1/calicoctl-linux-amd64 -o /root/tools/calicoctl'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['chmod +x /root/tools/calicoctl'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['mv /root/tools/calicoctl /usr/bin/'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['curl https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml -o /root/tools/calico.yaml'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['kubectl apply -f /root/tools/calico.yaml'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/apiserver.yaml'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['openssl req -x509 -nodes -newkey rsa:4096 -keyout /root/tools/apiserver.key -out /root/tools/apiserver.crt -days 365 -subj "/" -addext "subjectAltName = DNS:calico-api.calico-apiserver.svc"'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['kubectl create secret -n calico-apiserver generic calico-apiserver-certs --from-file=/root/tools/apiserver.key --from-file=/root/tools/apiserver.crt'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        check_call(['kubectl patch apiservice v3.projectcalico.org -p "{\\"spec\\": {\\"caBundle\\": \\"$(kubectl get secret -n calico-apiserver calico-apiserver-certs -o go-template=\'{{ index .data "apiserver.crt" }}\')\\"}}"'], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        
        print('Use the following command to join worker nodes to this cluster:')
        print(join_command)
        print()
        print('To join Windows node with ContainerD don\'t forget to add --cri-socket "npipe:////./pipe/containerd-containerd"')
        print(join_command + '--cri-socket "npipe:////./pipe/containerd-containerd"')
        
    elif node_type == "worker":
        print('Adding node to the cluster ...')
        
        check_call(['kubeadm join ' + controller_node + ':6443 --token ' + join_token + ' --discovery-token-ca-cert-hash sha256:' + discovery_token], stdout=open(os.devnull,'wb'), stderr=STDOUT, shell=True)
        
        print('If you plan to use the cluster with Windows worker nodes,\ndon\'t forget to run the followin commands on the controller node after adding the first Linux worker:\n\n')
        print('calicoctl patch felixconfiguration default -p \'{"spec":{"ipipEnabled":false}}\'')
        print('kubectl patch ipamconfigurations default --type merge --patch=\'{"spec": {"strictAffinity": true}}\'\n\n')
    
    print('Removing downloaded tools ...')
    check_call(['rm', '-rf', '/root/tools'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
    
    # print('Reboot ...')
    # os.system('reboot')

if __name__ == "__main__":
    main(sys.argv[1:])