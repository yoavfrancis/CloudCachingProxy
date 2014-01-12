__author__ = 'Yoav Francis and Tomer Cagan'

import time
import glob
import os
from boto.ec2 import EC2Connection
from boto.ec2.elb import ELBConnection, HealthCheck
from boto.regioninfo import RegionInfo

from config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, KEY_NAME, KEY_FILENAME, REGION

import paramiko
from paramiko import SSHClient
from scp import SCPClient


EC2_SECURITY_GROUP_NAME = "proxy-security-group"
EC2_SECURITY_GROUP_DESCRIPTION = "Security group for proxy project"
ELB_NAME = "proxy"
SLEEP_PERIOD = 5
LONG_SLEEP_PERIOD = 30
MAX_RETRIES = 3
PROXY_PORT = 8080
INSTANCE_TYPE = "t1.micro"
SAVED_AMI_NAME = 'proxy'
SAVED_AMI_DESCRIPTION = 'Caching proxy AMI'

# Our base machine - Ubuntu 13 AMI
BASE_AMI_ID = "ami-3d160149"
AMI_USERNAME = "ubuntu"
BASE_STARTUP_SCRIPT_NAME = 'proxy.sh'
STARTUP_SETUP_SCRIPT = 'startup_setup.sh'
FILE_DIRECTORY = "./files_to_upload"

CACHE_CONFIG_FILE = "cache.config"


def create_security_group():
    """
    Creates the ec2 security group
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                         aws_access_key_id=AWS_ACCESS_KEY,
                         region=RegionInfo(name=REGION,
                                           endpoint='ec2.%s.amazonaws.com' % REGION))

    if EC2_SECURITY_GROUP_NAME in [t.name for t in con.get_all_security_groups()]:
        print "Security group already exists, please be advised and manually delete it first"
        return False

    group = con.create_security_group(EC2_SECURITY_GROUP_NAME, EC2_SECURITY_GROUP_DESCRIPTION)
    try :
        print "Authorizing rules.."
        #Allow ssh (secured by key, but should be further limited to this machine IP only)
        group.authorize('tcp', 22, 22, "0.0.0.0/0")
        group.authorize('tcp', PROXY_PORT, PROXY_PORT, "0.0.0.0/0")
    except:
        print "Could not authorize security rules"

    con.close()

def delete_security_group(name=EC2_SECURITY_GROUP_NAME):
    """
    Deletes the ec2 security group. Must be called after instances were deleted
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                         aws_access_key_id=AWS_ACCESS_KEY,
                         region=RegionInfo(name=REGION,
                                           endpoint='ec2.%s.amazonaws.com' % REGION))

    group = [t for t in con.get_all_security_groups() if t.name == name]
    if len(group)==0:
        print "No security group to delete"
    else:
        print "deleting security group"
        group[0].delete()

    con.close()

def create_load_balancer():
    """
    Creates the load balancer and returns its DNS name
    """
    con = ELBConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                           endpoint='%s.elasticloadbalancing.amazonaws.com'% REGION))

    if ELB_NAME in [t.name for t in con.get_all_load_balancers()]:
        print "LB already exists, please be advised and manually delete it first"
        return False

    print "Creating load balancer.."
    lb = con.create_load_balancer(ELB_NAME,
                                    [REGION + "a", REGION + "b", REGION + "c"],
                                    [(PROXY_PORT, PROXY_PORT, "tcp")])

    print "Configure health check"
    healthcheck = HealthCheck(access_point=ELB_NAME,
                             target="TCP:%d" % PROXY_PORT,
                             interval=30,
                             healthy_threshold=2,
                             unhealthy_threshold=2,
                             timeout=2)

    lb.configure_health_check(healthcheck)

    print "Load balancer configured at : %s" % lb.dns_name
    return lb.dns_name


def delete_load_balancer():
    """
    Deletes our load balancer and deregister all instances from it
    """
    con = ELBConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                           endpoint='%s.elasticloadbalancing.amazonaws.com'% REGION))

    group = [t for t in con.get_all_load_balancers() if t.name == ELB_NAME]
    if len(group)==0:
        print "No load balancers to delete"
    else:
        print "deregister lb instances"
        group[0].deregister_instances([t.id for t in group[0].instances])
        time.sleep(SLEEP_PERIOD)
        print "deleting lb"
        group[0].delete()

def create_base_instance(cache_nodes_address_list):
    """
    Creates the base instances, configured to use the list of the given cache nodes
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='ec2.%s.amazonaws.com' % REGION))

    print "Creating base instance.."
    rev = con.run_instances(BASE_AMI_ID,
                            key_name=KEY_NAME,
                            instance_type=INSTANCE_TYPE,
                            security_groups=[EC2_SECURITY_GROUP_NAME],
                            placement="{0}a".format(REGION),
                            additional_info="proxy base instance",
                            user_data="#!/bin/bash\n\
                                        /home/{0}/{1}.".format(AMI_USERNAME, BASE_STARTUP_SCRIPT_NAME))

    print "Waiting for base instance to become ready"
    while rev.instances[0].update() != "running":
        time.sleep(SLEEP_PERIOD)

    print "Base instance is ready - customizing.."

    dnsname = rev.instances[0].dns_name
    print "address is : %s" % dnsname

    time.sleep(LONG_SLEEP_PERIOD)

    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(dnsname, username=AMI_USERNAME, key_filename=KEY_FILENAME)
    time.sleep(SLEEP_PERIOD)
    run_command(client, 'sudo sed -i "/^# deb.*multiverse/ s/^# //" /etc/apt/sources.list')
    run_command(client, "sudo apt-get update -y")
    run_command(client, "sudo apt-get install ec2-api-tools python-pip python-dev zlib1g-dev libmemcached-dev libmemcache-dev libmemcache0 -y")
    run_command(client, "sudo apt-get upgrade -y")
    run_command(client, "sudo pip install fabric ipython werkzeug boto paramiko scp pylibmc --upgrade")


    #create cache config file in the (files-to-upload) directory. the file contains the nodes address
    file(os.path.join(FILE_DIRECTORY,CACHE_CONFIG_FILE),"w").writelines("\n".join(cache_nodes_address_list))

    scpclient = SCPClient(client.get_transport())
    # upload all files in the code directory
    for fname in glob.glob(os.path.join(FILE_DIRECTORY, "*")):
        try:
            scpclient.put(fname, os.path.basename(fname))
        except:
            pass

    #Files uploaded, run script that copies modified rc.local to the original rc.local
    #rc.local script would run proxy.sh
    run_command(client, "sudo /home/{0}/{1}".format(AMI_USERNAME, STARTUP_SETUP_SCRIPT))

    print "address is : %s" % dnsname

    #Add "proxy" name tag
    rev.instances[0].add_tag('Name', SAVED_AMI_NAME)

    client.close()

    return rev.instances[0]

def run_command(sshclient, command):
    """
    Simply runs a command given the sshclient object
    """
    stdin, stdout, stderr = sshclient.exec_command(command)
    stdin.flush()
    data = stdout.read().splitlines()
    for line in data:
        print line

def create_base_ami(instance, wait_until_available=False):
    """
    Saves the base configured instance to an AMI snapshot for use in autoscaling
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='ec2.%s.amazonaws.com' % REGION))


    ami = con.create_image(instance.id, SAVED_AMI_NAME, SAVED_AMI_DESCRIPTION)
    print "New AMI creation task has been created, id : %s" % ami
    time.sleep(LONG_SLEEP_PERIOD)

    if wait_until_available:
        print "Waiting until AMI is available.. this might take a while.."
        while True:
            img = con.get_image(ami)
            if img.state == 'available':
                break;
            time.sleep(LONG_SLEEP_PERIOD)
        print "AMI is available !"
    else:
        print "AMI Task created - it may take a while until it is available"

    con.close()
    return ami

def get_instance(name=SAVED_AMI_NAME):
    """
    Returns an instance that matches the given name
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='ec2.%s.amazonaws.com' % REGION))
    for rev in con.get_all_instances():
        for instance in rev.instances:
            try:
                if instance.tags['Name'] == name and instance.state == 'running':
                    return instance
            except:
                pass
    con.close()
    return None



def delete_instances():
    """
    Deletes all ec2 instances that belong to the proxy, and contain its tag
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='ec2.%s.amazonaws.com' % REGION))
    instance_ids = []
    for rev in con.get_all_instances():
        for instance in rev.instances:
            try:
                if instance.tags['Name'] == SAVED_AMI_NAME:
                    instance_ids.append(instance.id)
            except:
                pass

    print "Terminating instances : " + str(instance_ids)
    con.terminate_instances(instance_ids)

    con.close()


def delete_ami():
    """
    Deletes the autoscaling-used ami
    """
    con = EC2Connection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='ec2.%s.amazonaws.com' % REGION))


    for img in con.get_all_images(owners=['self']):
        if img.name== SAVED_AMI_NAME:
            print "Deregistering image : %s" % img.name
            con.deregister_image(img.id)
            break

    con.close()

