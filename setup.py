__author__ = 'Yoav Francis and Tomer Cagan'

import ec2
import elasticache
import sns
import autoscaling
import time
import dynamodb

LONG_SLEEP_PERIOD = 30

def setup():
    """
    Performs base orchestration of the AMI creation
    """

    print "Creating cache nodes"
    elasticache.create_cache()
    cache_nodes_addresses = elasticache.get_cluster_nodes()

    print "Creating dynamodb table"
    dynamodb.upload_dynamo()

    #Create base ami and configure it to use the elasticache nodes
    ec2.create_security_group()
    print "Creating ec2 base instance and ami"
    lb_dns = ec2.create_load_balancer()


    instance = ec2.create_base_instance(cache_nodes_addresses)
    ami = ec2.create_base_ami(instance, True)

    print "Creating sns notifications"
    topic_arn = sns.create_sns_topic()
    sns.create_email_topic_subscription()


    print "Configuring autoscaling"
    autoscaling.create_autoscaling(ami, topic_arn)

    print "Base orchestration is done. Connect to the proxy at : %s:%d" % (lb_dns, ec2.PROXY_PORT)

def clean_all():
    """
    Tears done and cleans up the entire proxy cloud orchestration.
    """

    print "deleting dynamodb.."
    dynamodb.delete_dynamodb()

    print "deleting elasticache"
    elasticache.destroy_cache()

    print "deleting load balancer"
    ec2.delete_load_balancer()

    print "deleting ami"
    ec2.delete_ami()

    print "deleting sns"
    sns.delete_sns_subscription()
    sns.delete_sns_topic()

    print "deleting autoscaling"
    autoscaling.delete_autoscaling()

    print "deleting instances"
    ec2.delete_instances()

    time.sleep(LONG_SLEEP_PERIOD)

    #Must delete after the autoscaling deletion, as it contains the autoscaling machines in the group
    print "deleting security group"
    ec2.delete_security_group()

