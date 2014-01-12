__author__ = 'Yoav Francis and Tomer Cagan'

import time
from boto.elasticache.layer1 import ElastiCacheConnection
from boto.exception import BotoServerError
from boto.regioninfo import RegionInfo
from config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, REGION

CACHE_SECURITY_GROUP_NAME = "proxy-security-group"
CACHE_SECURITY_GROUP_DESCRIPTION = "proxy cache security group"
EC2_SECURITY_GROUP_NAME = "proxy"
SLEEP_PERIOD = 5
LONG_SLEEP_PERIOD = 30
MAX_RETRIES = 3
AWS_ACCOUNT_OWNER_ID = "721687699245"
CACHE_CLUSTER_NAME = "proxy"
NUM_CACHE_NODES = 2
CACHE_NODE_TYPE = "cache.t1.micro"
CACHE_ENGINE = "Memcached"
CACHE_PORT = 11211



def create_cache():
    """
    Creates our cache clusters
    """
    con = ElastiCacheConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                aws_access_key_id=AWS_ACCESS_KEY,
                                region=RegionInfo(name=REGION,
                                                  endpoint='elasticache.%s.amazonaws.com' % REGION))


    print "Creating cache security group"
    try:
        con.create_cache_security_group(CACHE_SECURITY_GROUP_NAME,
                                        CACHE_SECURITY_GROUP_DESCRIPTION)
    except Exception:
        print "Security group already exist"
        con.close()
        return

    print "Waiting for cache security group to be created"
    tries = MAX_RETRIES
    while tries > 0:
        try :
            con.describe_cache_security_groups(CACHE_SECURITY_GROUP_NAME)
        except BotoServerError:
            time.sleep(SLEEP_PERIOD)
        tries-=1

    print "Authorizing cache security group with ec2 security group"
    con.authorize_cache_security_group_ingress(CACHE_SECURITY_GROUP_NAME,
                                               EC2_SECURITY_GROUP_NAME,
                                               AWS_ACCOUNT_OWNER_ID)
    time.sleep(SLEEP_PERIOD)


    # Create the cache cluster
    con.create_cache_cluster(CACHE_CLUSTER_NAME,
                             NUM_CACHE_NODES,
                             CACHE_NODE_TYPE,
                             CACHE_ENGINE,
                             cache_security_group_names=[CACHE_SECURITY_GROUP_NAME],
                             port = CACHE_PORT,
                             preferred_availability_zone="{0}a".format(REGION))

    print "Waiting for cache cluster to initialize"
    while True:
        if get_cluster_status() != 'available':
            time.sleep(SLEEP_PERIOD)
        else:
            break

    print "Cache cluster created successfully"
    con.close()


def get_cluster_status():
    con = ElastiCacheConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                aws_access_key_id=AWS_ACCESS_KEY,
                                region=RegionInfo(name=REGION,
                                                  endpoint='elasticache.%s.amazonaws.com' % REGION))


    rep = con.describe_cache_clusters(cache_cluster_id=CACHE_CLUSTER_NAME,
                                      show_cache_node_info=True)
    cluster = rep["DescribeCacheClustersResponse"]\
                 ["DescribeCacheClustersResult"]\
                 ["CacheClusters"]\
                 [0]

    status = cluster['CacheClusterStatus']
    con.close()
    return status

def get_cluster_nodes():
    """
    returns the memcache nodes addresses in a list, ready to be used.
    """
    con = ElastiCacheConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                aws_access_key_id=AWS_ACCESS_KEY,
                                region=RegionInfo(name=REGION,
                                                  endpoint='elasticache.%s.amazonaws.com' % REGION))


    rep = con.describe_cache_clusters(cache_cluster_id=CACHE_CLUSTER_NAME,
                                      show_cache_node_info=True)
    cluster = rep["DescribeCacheClustersResponse"]\
                 ["DescribeCacheClustersResult"]\
                 ["CacheClusters"]\
                 [0]
    result = []
    for node in cluster['CacheNodes']:
        result.append("%s:%d" % (node["Endpoint"]['Address'],
                                 node["Endpoint"]['Port']))

    con.close()
    return result

def destroy_cache():
    """
    Destroys our cache cluster
    """
    con = ElastiCacheConnection(aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                aws_access_key_id=AWS_ACCESS_KEY,
                                region=RegionInfo(name=REGION,
                                                  endpoint='elasticache.%s.amazonaws.com' % REGION))


    print "Deleting cache cluster"
    try:
        con.delete_cache_cluster(CACHE_CLUSTER_NAME)
        while True:
            try:
                if get_cluster_status() == 'deleting':
                    time.sleep(SLEEP_PERIOD)
            except:
                #Exception is thrown when cluster does not exist and attempting to describe it
                break
    except:
        print "Exception when deleting cache cluster"
    finally:
        print "Deleting cache security group"
        con.delete_cache_security_group(CACHE_SECURITY_GROUP_NAME)
        con.close()
