__author__ = 'Tomer Cagan and Yoav Francis'

from boto.dynamodb2.fields import HashKey, RangeKey, KeysOnlyIndex, AllIndex
from boto.dynamodb2.table import Table
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.regioninfo import RegionInfo

from config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, REGION
from ad_block_schema import EASY_LIST_TBL, EASY_LIST_TBL_KEY, EASY_LIST_TBL_ATTR,\
                            DOMAIN_LIST_KEY, RESOURCE_LIST_KEY, QUERY_LIST_KEY


class AdBlocker(object):
    """
    Ad Blocking class that manage its own data and exposes functionality for determine if a resource should be blocked
    """

    def __init__(self):
        self.domain_list = []
        self.resource_list = []
        self.query_list = []

    def load_data(self):
        con = DynamoDBConnection(aws_access_key_id=AWS_ACCESS_KEY,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                              region = RegionInfo(name=REGION,
                                                  endpoint='dynamodb.%s.amazonaws.com' % REGION))



        easylist_table = Table(EASY_LIST_TBL, connection=con)

        #get the lists
        value = easylist_table.get_item(filter_type= DOMAIN_LIST_KEY)
        self.domain_list = list(value[EASY_LIST_TBL_ATTR])

        value = easylist_table.get_item(filter_type= RESOURCE_LIST_KEY)
        self.resource_list = list(value[EASY_LIST_TBL_ATTR])

        value = easylist_table.get_item(filter_type= QUERY_LIST_KEY)
        self.query_list = list(value[EASY_LIST_TBL_ATTR])

    def is_blocked(self, domain, resource, query):
        """
        Determine if the resource should be blocked
        """
        for d in self.domain_list:
           if d in domain:
                return True

        if len(resource) > 0:
            for r in self.resource_list:
                if r in resource:
                    return True

        if len(query) > 0:
            for q in self.query_list:
                if q in query:
                    return True

        return False



if __name__ == "__main__":
    blocker = AdBlocker()

    blocker.load_data()

    print "blocking {0} domains".format(len(blocker.domain_list))

    print "Block \".za/ads\": {0}".format(blocker.is_blocked(".za/ads", "", ""))

    print "Block \"tomercagan.com\": {0}".format(blocker.is_blocked("tomercagan.com", "/index.html", ""))


