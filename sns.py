__author__ = 'Yoav Francis and Tomer Cagan'

from config import AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY, REGION, SNS_EMAIL
from boto.sns import SNSConnection
from boto.regioninfo import RegionInfo

SNS_TOPIC_NAME = "proxy"

def create_sns_topic():
    """
    Creates the SNS topic and returns the topic arn string
    """
    con = SNSConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='sns.%s.amazonaws.com' % REGION))

    topic_arn = con.create_topic(SNS_TOPIC_NAME)
    topic_arn = topic_arn['CreateTopicResponse']['CreateTopicResult']['TopicArn']
    print "Topic created, arn is : %s" % topic_arn
    con.close()
    return topic_arn

def create_email_topic_subscription():
    """
    Creates the email subscription for our topic. Topic must be created prior to that.
    returns nothing.
    """
    con = SNSConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='sns.%s.amazonaws.com' % REGION))
    topic_arn = get_topic_arn()
    subscription = con.subscribe(topic_arn, "email", SNS_EMAIL)
    print "Subscribed email : %s to SNS notifications" % SNS_EMAIL
    print subscription
    print "Please make sure to check your inbox and confirm your subscription"
    con.close()

def delete_sns_subscription():
    """
    Deletes the SNS email subscription
    """
    con = SNSConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='sns.%s.amazonaws.com' % REGION))

    topic_arn = get_topic_arn()
    subscriptions = con.get_all_subscriptions_by_topic(topic_arn)['ListSubscriptionsByTopicResponse']\
                                                                 ['ListSubscriptionsByTopicResult']\
                                                                 ['Subscriptions']
    for s in subscriptions:
        try:
            print "Unsubscribing %s" % s
            con.unsubscribe(s['SubscriptionArn'])
        except:
            print "Could not unsubscribe %s" % s

    con.close()

def delete_sns_topic():
    """
    Deletes the SNS topic. Subscriptions must be deleted prior to that.
    """
    con = SNSConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='sns.%s.amazonaws.com' % REGION))

    topic_arn = get_topic_arn()

    print "Deleting topic : %s" % topic_arn
    con.delete_topic(topic_arn)
    con.close()

def get_topic_arn(topicname = SNS_TOPIC_NAME):
    """
    Returns the topic arn, using our default SNS_TOPIC_NAME or a given parameter
    """
    con = SNSConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        aws_access_key_id=AWS_ACCESS_KEY,
                        region=RegionInfo(name=REGION,
                                          endpoint='sns.%s.amazonaws.com' % REGION))
    for t in con.get_all_topics()['ListTopicsResponse']['ListTopicsResult']['Topics']:
        topicarn = t['TopicArn']
        if SNS_TOPIC_NAME in topicarn:
            con.close()
            return topicarn


    con.close()
    return None