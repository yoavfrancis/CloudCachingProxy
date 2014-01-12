__author__ = 'Tomer Cagan and Yoav Francis'

from config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, KEY_NAME, REGION
from boto.regioninfo import RegionInfo
from boto.ec2.autoscale import AutoScaleConnection, LaunchConfiguration, AutoScalingGroup, ScalingPolicy
from boto.ec2.cloudwatch import MetricAlarm, CloudWatchConnection
from boto.ec2.autoscale.tag import  Tag
import time
import sns

AUTOSCALING_MIN_INSTANCES = 1
AUTOSCALING_MAX_INSTANCES = 4
AUTOSCALING_COOLDOWN_PERIOD = 180

# CPU Threshold scaling parameters
AUTOSCALING_CPU_MAX_THRESHOLD= 70
AUTOSCALING_CPU_MIN_THRESHOLD = 40

AUTOSCALING_GROUP_NAME = "proxy-autoscaling"

SLEEP_PERIOD = 5
LONG_SLEEP_PERIOD = 30
EC2_SECURITY_GROUP_NAME = 'proxy'
ELB_NAME = 'proxy'
INSTANCE_TYPE = 't1.micro'

def create_autoscaling(ami_id, sns_arn):
    """
    Creates the autoscaling group for proxy instances
    Inspired by boto autoscaling tutorial.
    """
    con = AutoScaleConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                              aws_access_key_id=AWS_ACCESS_KEY,
                              region=RegionInfo(name=REGION,
                                               endpoint='autoscaling.%s.amazonaws.com' % REGION))



    print "Creating autoscaling configuration.."
    config = LaunchConfiguration(name=AUTOSCALING_GROUP_NAME,
                                 image_id=ami_id,
                                 key_name=KEY_NAME,
                                 security_groups=[EC2_SECURITY_GROUP_NAME],
                                 instance_type=INSTANCE_TYPE)

    con.create_launch_configuration(config)


    print "Create autoscaling group..."
    ag = AutoScalingGroup(name=AUTOSCALING_GROUP_NAME,
                          launch_config=config,
                          availability_zones=["{0}a".format(REGION)],
                          load_balancers=[ELB_NAME],
                          min_size=AUTOSCALING_MIN_INSTANCES,
                          max_size=AUTOSCALING_MAX_INSTANCES,
                          group_name=AUTOSCALING_GROUP_NAME)
    con.create_auto_scaling_group(ag)

    # fetch the autoscale group after it is created (unused but may be necessary)
    _ = con.get_all_groups(names=[AUTOSCALING_GROUP_NAME])[0]

    # Create tag name for autoscaling-created machines
    as_tag = Tag(key='Name', value=AUTOSCALING_GROUP_NAME, propagate_at_launch=True, resource_id=AUTOSCALING_GROUP_NAME)
    con.create_or_update_tags([as_tag])


    print "Creating autoscaling policy..."
    scaleup_policy = ScalingPolicy(name='scale_up',
                                   adjustment_type='ChangeInCapacity',
                                   as_name=AUTOSCALING_GROUP_NAME,
                                   scaling_adjustment=1,
                                   cooldown=AUTOSCALING_COOLDOWN_PERIOD)

    scaledown_policy = ScalingPolicy(name='scale_down',
                                     adjustment_type='ChangeInCapacity',
                                     as_name=AUTOSCALING_GROUP_NAME,
                                     scaling_adjustment=-1,
                                     cooldown=AUTOSCALING_COOLDOWN_PERIOD)

    con.create_scaling_policy(scaleup_policy)
    con.create_scaling_policy(scaledown_policy)

    # Get freshened policy objects
    scaleup_policy = con.get_all_policies(as_group=AUTOSCALING_GROUP_NAME, policy_names=['scale_up'])[0]
    scaledown_policy = con.get_all_policies(as_group=AUTOSCALING_GROUP_NAME, policy_names=['scale_down'])[0]

    print "Creating cloudwatch alarms"
    cloudwatch_con = CloudWatchConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                      aws_access_key_id=AWS_ACCESS_KEY,
                                      region=RegionInfo(name=REGION,
                                                        endpoint='monitoring.%s.amazonaws.com' % REGION))


    alarm_dimensions = {"AutoScalingGroupName": AUTOSCALING_GROUP_NAME}
    scaleup_alarm = MetricAlarm(name='scale_up_on_cpu',
                                namespace='AWS/EC2',
                                metric='CPUUtilization',
                                statistic='Average',
                                comparison='>',
                                threshold=AUTOSCALING_CPU_MAX_THRESHOLD,
                                period='60',
                                evaluation_periods=1,
                                alarm_actions=[scaleup_policy.policy_arn, sns_arn],
                                dimensions=alarm_dimensions)

    # Don't send SNS on scaledown policy
    scaledown_alarm = MetricAlarm(name='scale_down_on_cpu',
                                 namespace='AWS/EC2',
                                 metric='CPUUtilization',
                                 statistic='Average',
                                 comparison='<',
                                 threshold=AUTOSCALING_CPU_MIN_THRESHOLD,
                                 period='60',
                                 evaluation_periods=1,
                                 alarm_actions=[scaledown_policy.policy_arn],
                                 dimensions=alarm_dimensions)
    cloudwatch_con.create_alarm(scaleup_alarm)
    cloudwatch_con.create_alarm(scaledown_alarm)


def delete_autoscaling():
    con = AutoScaleConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                              aws_access_key_id=AWS_ACCESS_KEY,
                              region=RegionInfo(name=REGION,
                                               endpoint='autoscaling.%s.amazonaws.com' % REGION))

    print "Deleting autoscaling group.."
    group = con.get_all_groups(names=[AUTOSCALING_GROUP_NAME])[0]
    print "shutting down instances"
    group.shutdown_instances()
    time.sleep(LONG_SLEEP_PERIOD)
    print "Deleting autoscaling group itself"
    con.delete_auto_scaling_group(AUTOSCALING_GROUP_NAME, force_delete=True)
    print "Deleting launch configuration"
    con.delete_launch_configuration(AUTOSCALING_GROUP_NAME)



    con.close()
