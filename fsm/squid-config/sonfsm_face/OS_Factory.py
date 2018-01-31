#!/usr/bin/env python3

import os
import logging
import paramiko
from abc import ABCMeta, abstractmethod

class Factory:
    def get_os_implementation(self, os, logger):
        if os == "\"centos\"":
            return Centos_implementation(logger)
        elif os == "ubuntu":
            return Ubuntu_implementation(logger)
        else:
            return Centos_implementation(logger)
            #raise NotImplementedError("Unknown OS type.")

class OS_implementation(metaclass = ABCMeta):
    config_options = { 'direct': './ansible/roles/squid/files/squid_direct.conf', 
        'transparent': './ansible/roles/squid/files/squid.conf', 
        'squidguard': './ansible/roles/squid/files/squid_guard.conf' }
    config_dir = './ansible/roles/squid/files'
    LOG = None

    def __init__(self, logger):
        self.LOG = logger
    
    @abstractmethod
    def configure_interfaces(self, ssh = None):
        raise NotImplementedError("Not implemented")
    
    @abstractmethod
    def configure_squid_forwarding_rules(self, ssh, gw):
        raise NotImplementedError("Not implemented")

    def configure_monitoring(self, ssh, host_ip):
        ftp = ssh.open_sftp()
        LOG.info("SFTP connection established")

        self.createConf(host_ip, 4, 'cache-vnf')
        localpath = self.monitoring_file
        LOG.info("SFTP connection entering on %s", localpath)
        remotepath = '/tmp/node.conf'
        sftpa = ftp.put(localpath, remotepath)
        ftp.close()

        LOG.info("SSH connection reestablished")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo cp /tmp/node.conf /opt/Monitoring')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl restart mon-probe.service')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
                
    def stop_service(self, ssh):
        LOG.info("SSH connection established")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl stop squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
        
    def scale_service(self, ssh):
        LOG.info("SSH connection established")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl start squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))

    @abstractmethod
    def reconfigure_service(self, ssh):
        raise NotImplementedError("Not implemented")
        
    @abstractmethod
    def configure_forward_routing(self, ssh):
        raise NotImplementedError("Not implemented")
    
    def createConf(self, pw_ip, interval, name):

        #config = configparser.RawConfigParser()
        config = configparser.ConfigParser(interpolation = None)
        config.add_section('vm_node')
        config.add_section('Prometheus')
        config.set('vm_node', 'node_name', name)
        config.set('vm_node', 'post_freq', str(interval))
        config.set('Prometheus', 'server_url', 'http://' + pw_ip + ':9091/metrics')
    
    
        with open('node.conf', 'w') as configfile:    # save
            config.write(configfile)
    
        f = open('node.conf', 'r')
        LOG.debug('Mon Config-> ' + "\n" + f.read())
        f.close()
    
class Centos_implementation(OS_implementation):
    
    def __init__(self, logger):
        OS_implementation(logger)
    
    def configure_interfaces(self, ssh, config_dir):
        LOG.info("configure_interfaces centos")
        
        if ssh == None:
            return;
        
        LOG.info("Copy net interfaces cfg files")
        ftp = ssh.open_sftp()
        LOG.info("SFTP connection established")

        localpath = config_dir + '/ifcfg-eth1'
        LOG.info("SFTP connection entering on %s", localpath)
        remotepath = '/tmp/ifcfg-eth1'
        sftpa = ftp.put(localpath, remotepath)
        localpath = config_dir + '/ifcfg-eth2'
        remotepath = '/tmp/ifcfg-eth2'
        LOG.info("SFTP connection entering on %s", localpath)
        sftpa = ftp.put(localpath, remotepath)
        ftp.close()

        LOG.info("Copying scripts")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo cp /tmp/ifcfg-eth1 /etc/sysconfig/network-scripts && sudo cp /tmp/ifcfg-eth2 /etc/sysconfig/network-scripts")
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Displaying eth1 data")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/sbin/ifconfig eth1")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("echo \"HWADDRESS=\"$(/sbin/ifconfig eth2 | awk '/ether/ { print $2 } ') | sudo su -c 'cat >> /etc/sysconfig/network-scripts/ifcfg-eth2'")
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Updating ifcfg-eth1")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("echo \"HWADDRESS=\"$(/sbin/ifconfig eth1 | awk '/ether/ { print $2 } ') | sudo su -c 'cat >> /etc/sysconfig/network-scripts/ifcfg-eth1'")
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Get current default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/usr/sbin/ip route | awk '/default/ { print $3 }'")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))
        return sout.strip()

    def configure_squid_forwarding_rules(self, ssh, gw):

        LOG.info("Always use eth0 (mgmt) for connection to 10.230.x.x for protecting admin ssh connections")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo /usr/sbin/ip route add 10.230.0.0/16 dev eth0 via {0}".format(gw))
        # FIX: how to known that eth0 is always mgmt ?
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

        LOG.info('iptables configuration to redirect port 80 to 3128')
        LOG.info('get own ip')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/sbin/ifconfig eth0 | grep \"inet\" | awk '{ if ($1 == \"inet\") {print $2} }'")
        my_ip = ssh_stdout.read().decode('utf-8')
        LOG.info('stdout from remote: ' + my_ip)
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info('Port 80 to 3128 for {0}'.format(my_ip))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /usr/sbin/iptables -t nat -A PREROUTING -i eth0 -p tcp -m tcp --dport 80 -j DNAT --to-destination {0}:3128".format(my_ip))
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Redirecting port")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo /usr/sbin/iptables -t nat -A PREROUTING -i eth0 -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 3128')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Setting masquerade")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo /usr/sbin/iptables -t nat -A POSTROUTING -o eth2 -j MASQUERADE')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Accept in the filter table")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo /usr/sbin/iptables -t filter -A INPUT -p tcp --dport 3128 -j ACCEPT')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))
        
        LOG.info("Configuration of squid service")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl start squid start')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

    def reconfigure_service(self, ssh, cfg):
        LOG.info("SSH connection established")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl stop squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
        
        ftp = ssh.open_sftp()
        LOG.info("SFTP connection established")

        localpath = self.config_options[config]
        LOG.info("SFTP connection entering on %s", localpath)
        remotepath = '/tmp/squid.conf'
        sftpa = ftp.put(localpath, remotepath)
        ftp.close()

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo mv /etc/squid/squid.conf /etc/squid/squid.conf.old')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo cp /tmp/squid.conf /etc/squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl restart squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr)) 

    def configure_forward_routing(self, ssh):
        LOG.info("Retrieve FSM IP address")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "FSM_IP=$(echo $SSH_CLIENT | awk '{ print $1}') && echo $FSM_IP")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))
        fsm_ip = sout.strip()
        LOG.info("FSM IP: {0}".format(fsm_ip))

        LOG.info("Get current default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("IP=$(/usr/sbin/ip route | awk '/default/ { print $3 }') && echo $IP")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))
        default_gw = sout.strip()
        LOG.info("Default GW: {0}".format(str(default_gw)))

        LOG.info("Configure route for FSM IP")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo /usr/sbin/route add -net {0} netmask 255.255.255.255 gw {1}"
            .format(fsm_ip, default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}"
            .format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

        # remove default GW
        LOG.info("Delete default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /usr/sbin/route del default gw {0}".format(default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

        # next VNF exists
        if next_ip is not None:
            # find virtual link of vpn output
            LOG.info("cpmgmt IP address:'{0}'; cpinput IP address:'{1}'; forward_cpinput_ip:'{2}'"
                .format(host_ip, data_ip, next_ip))

            LOG.info("Configure default GW for next VNF VM in chain using the eth2 (output) interface")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /usr/sbin/route add default gw {0} dev eth2".format(next_ip))
            LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))
        else:
            LOG.info("Modify DHCP configuration of interfaces")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo sed -i \"/DEFROUTE/cDEFROUTE=\"no\"\" /etc/sysconfig/network-scripts/ifcfg-eth0")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo sed -i \"/DEFROUTE/cDEFROUTE=\"no\"\" /etc/sysconfig/network-scripts/ifcfg-eth1")
            LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo sed -i \"/DEFROUTE/cDEFROUTE=\"yes\"\" /etc/sysconfig/network-scripts/ifcfg-eth2")
            LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

            LOG.info("Add default route for input/output interface (eth2)")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo dhclient -r eth2 && dhclient eth2")
            LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo sed -i \'s/#net.ipv4.ip_forward/net.ipv4.ip_forward/g\' /etc/sysctl.conf")
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))
        
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo systemctl restart network.service")
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

  
class Ubuntu_implementation(OS_implementation):
    
    def __init__(self, logger):
        OS_implementation(logger)
  
    def configure_interfaces(self, ssh):
        LOG.info("configure_interfaces Ubuntu")
        
        if ssh == None:
            return;
        
        LOG.info("Copy net interfaces cfg files")
        ftp = ssh.open_sftp()
        LOG.info("SFTP connection established")

        localpath = config_dir + '/50-cloud-init.cfg'
        LOG.info("SFTP connection entering on %s", localpath)
        remotepath = '/tmp/50-cloud-init.cfg'
        sftpa = ftp.put(localpath, remotepath)
        ftp.close()

        LOG.info("Copying scripts")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo cp /tmp/50-cloud-init.cfg /etc/network/interfaces.d")
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Displaying eth1 data")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/sbin/ifconfig eth1")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))

        LOG.info("Force ip forwarding")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("echo '1' | sudo tee /proc/sys/net/ipv4/ip_forward")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))

        LOG.info("Get eth1 (input) subnetwork")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/sbin/ip route list | grep -m 1 '/27 dev eth1' | awk '{printf \"%s\",$1}'")
        input_subnetwork = ssh_stdout.read().decode('utf-8').strip()
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(input_subnetwork, serr))

        LOG.info("Delete extraneous rule on eth2 (output)")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /sbin/ip route del {0} dev eth2".format(input_subnetwork))
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))

        LOG.info("Get current default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/sbin/ip route | awk '/default/ { print $3 }'")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))
        return sout.strip()

    def configure_squid_forwarding_rules(self, ssh, gw):

        LOG.info("Always use eth0 (mgmt) for connection to 10.230.x.x for protecting admin ssh connections")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo /sbin/ip route add 10.230.0.0/16 dev eth0 via {0}".format(gw))
        # FIX: how to known that eth0 is always mgmt ?
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

        LOG.info('iptables configuration to redirect port 80 to 3128')
        LOG.info('get own ip')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/sbin/ifconfig ens3 | grep \"inet\" | awk '{ if ($1 == \"inet\") {print $2} }' | cut -b 6-")
        my_ip = ssh_stdout.read().decode('utf-8')
        LOG.info('stdout from remote: ' + my_ip)
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info('Port 80 to 3128 for {0}'.format(my_ip))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /sbin/iptables -t nat -A PREROUTING -i eth0 -p tcp -m tcp --dport 80 -j DNAT --to-destination {0}:3128".format(my_ip))
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Redirecting port")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo /sbin/iptables -t nat -A PREROUTING -i eth0 -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 3128')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Setting masquerade")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo /sbin/iptables -t nat -A POSTROUTING -o eth2 -j MASQUERADE')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

        LOG.info("Accept in the filter table")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo /sbin/iptables -t filter -A INPUT -p tcp --dport 3128 -j ACCEPT')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))
        
        LOG.info("Configuration of squid service")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl start squid')
        LOG.info('stdout from remote: ' + ssh_stdout.read().decode('utf-8'))
        LOG.info('stderr from remote: ' + ssh_stderr.read().decode('utf-8'))

    def reconfigure_service(self, ssh):
        LOG.info("SSH connection established")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl stop squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
        
        ftp = ssh.open_sftp()
        LOG.info("SFTP connection established")

        localpath = self.config_options[config]
        LOG.info("SFTP connection entering on %s", localpath)
        remotepath = '/tmp/squid.conf'
        sftpa = ftp.put(localpath, remotepath)
        ftp.close()

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo mv /etc/squid3/squid.conf /etc/squid3/squid.conf.old')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo cp /tmp/squid.conf /etc/squid3')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr))

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl restart squid')
        LOG.info('output from remote: ' + str(ssh_stdout))
        LOG.info('output from remote: ' + str(ssh_stdin))
        LOG.info('output from remote: ' + str(ssh_stderr)) 

    def configure_forward_routing(self, ssh):
        LOG.info("Retrieve FSM IP address")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "FSM_IP=$(echo $SSH_CLIENT | awk '{ print $1}') && echo $FSM_IP")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))
        fsm_ip = sout.strip()
        LOG.info("FSM IP: {0}".format(fsm_ip))

        LOG.info("Get current default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "IP=$(/sbin/ip route | awk '/default/ { print $3 }') && echo $IP")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))
        default_gw = sout.strip()
        LOG.info("Default GW: {0}".format(str(default_gw)))

        LOG.info("Configure route for FSM IP")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo /sbin/route add -net {0} netmask 255.255.255.255 gw {1}"
            .format(fsm_ip, default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}"
            .format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

        # remove default GW
        LOG.info("Delete default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "sudo /sbin/route del default gw {0}".format(default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(ssh_stdout.read().decode('utf-8'),
                         ssh_stderr.read().decode('utf-8')))

        # next VNF exists
        if next_ip is not None:
            # find virtual link of vpn output
            LOG.info("cpmgmt IP address:'{0}'; cpinput IP address:'{1}'; forward_cpinput_ip:'{2}'"
                .format(host_ip, data_ip, next_ip))

            LOG.info("Force the path to the next hope to go through eth2 (outpu)")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /sbin/ip route add {0}/32 dev eth2".format(next_ip))
            sout = ssh_stdout.read().decode('utf-8')
            serr = ssh_stderr.read().decode('utf-8')
            LOG.info("stdout: {0}\nstderr:  {1}".format(sout, serr))

            LOG.info("Configure default GW for next VNF VM in chain using the eth2 (output) interface")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "sudo /sbin/route add default gw {0} dev eth2".format(next_ip))
            LOG.info("stdout: {0}\nstderr:  {1}"
                     .format(ssh_stdout.read().decode('utf-8'),
                             ssh_stderr.read().decode('utf-8')))
        else:
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "LI = $(\"sudo /sbin/ifconfig ens3 | grep \"inet\" | awk '{if($1==\"inet\") { print $2; }}' | cut -b 6-\") && echo $LI")
            last_if = ssh_stdout.read().decode('utf-8').split('.')
            last_if[3] = '1'
            str_out = "supersede routers %s;".format('.'.join(last_if))
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo echo %s >>  /etc/dhcp/dhclient.conf".format(str_out))

        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo sed -i \'s/#net.ipv4.ip_forward/net.ipv4.ip_forward/g\' /etc/sysctl.conf")
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))
        
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo /etc/init.d/procps restart")
        LOG.info("stdout: {0}\nstderr:  {1}".format(ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')))

