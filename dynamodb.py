__author__ = 'Yoav Francis and Tomer Cagan'

import sys
import os
import time
import traceback

from argparse import ArgumentParser

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.table import Table
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.regioninfo import RegionInfo

from config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, REGION
from ad_block_schema import EASY_LIST_TBL, EASY_LIST_TBL_KEY, EASY_LIST_TBL_ATTR, DOMAIN_LIST_KEY, RESOURCE_LIST_KEY, QUERY_LIST_KEY

EASYLIST_FILE_PATH = "easylist.txt"
LINE_BORDER = "**************************************"

IGNORE_PREFIX_LIST = ["[", "!", "-", "#", "@", "|", ",", "+"]

def upload_dynamo():
    """
    dynamodb.py
    Uploads the given easy list (add blocking) file to dynamodb.
    """
    print "Connecting to DynamoDB..."

    conn = DynamoDBConnection(aws_access_key_id=AWS_ACCESS_KEY,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                              region = RegionInfo(name=REGION,
                                                  endpoint='dynamodb.{0}.amazonaws.com'.format(REGION)))

    print "\tConnected!"

     # Create the tables or use already existing ones
    print "Getting tables..."

    #define expected throughput
    throughput = { 'read': 2, 'write': 5 }

    #define the schema - in our case a simple key
    easylist_tbl_schema = [HashKey(EASY_LIST_TBL_KEY)]

    easylist_table = None

    #get existing tables to check if need to create tables
    existing_tables = conn.list_tables()[u"TableNames"]

    if EASY_LIST_TBL not in existing_tables:
        print "\ttrying to create {0} table...".format(EASY_LIST_TBL)
        try:
            easylist_table = Table.create(EASY_LIST_TBL, schema=easylist_tbl_schema, throughput=throughput, connection=conn)
            # Wait some for the tables to be created.
            time.sleep(60)
            print "\t\ttable created!"
        except:
            print "\t\t{0} table does not exist and could not be created. Quiting".format(EASY_LIST_TBL)
            return
    else:
        print "\ttable {0} already exists".format(EASY_LIST_TBL)
        easylist_table = Table(EASY_LIST_TBL, schema=easylist_tbl_schema, throughput=throughput, connection=conn)

    #read csv file and upload to db

    domain_list = []
    resource_list = []
    query_list = []

    #with easylist_table.batch_write() as batch:
    with open(EASYLIST_FILE_PATH, 'r') as reader:
        for line in reader.readlines():
            if line[0] in IGNORE_PREFIX_LIST or "##" in line:
                continue

            token = line.strip()

            if line[0] == "&":
                query_list.append(token)
            elif line[0] == "/":
                resource_list.append(token)
            else:
                domain_list.append(token)

                #batch.put_item(data = { EASY_LIST_TBL_KEY: token, EASY_LIST_TBL_ATTR: token})

    print "Loading the list to table"
    easylist_table.put_item( data={ EASY_LIST_TBL_KEY: DOMAIN_LIST_KEY, EASY_LIST_TBL_ATTR: set(domain_list) })
    #there is size limit - consider storing some other way
    easylist_table.put_item( data={ EASY_LIST_TBL_KEY: RESOURCE_LIST_KEY, EASY_LIST_TBL_ATTR: set(resource_list[100:1100]) })
    easylist_table.put_item( data={ EASY_LIST_TBL_KEY: QUERY_LIST_KEY, EASY_LIST_TBL_ATTR: set(query_list) })

    conn.close()
    print "Finished uploading easy list"

def delete_dynamodb():

    conn = DynamoDBConnection(aws_access_key_id=AWS_ACCESS_KEY,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                              region = RegionInfo(name=REGION,
                                                  endpoint='dynamodb.{0}.amazonaws.com'.format(REGION)))

    conn.delete_table(EASY_LIST_TBL)
    conn.close()

def get_argparse():
    """
    Create a command line argument parser for this program
    """
    cli_parser = ArgumentParser(description="Upload CSV file to a Dynamo DB instance")
    cli_parser.add_argument("input_file", help="The CSV file to upload")
    cli_parser.add_argument("-m", "-num_rows", dest="num_rows", type=int,
                            help="Number of rows to load to load to database")

    cli_parser.add_argument("-k", "-aws_key", dest="aws_key", help="The AWS key to use for authentication", default = AWS_ACCESS_KEY)

    cli_parser.add_argument("-s", "-aws_secret", dest="aws_secret", help="AWS secret key for authentication", default = AWS_SECRET_ACCESS_KEY)

    cli_parser.add_argument("-r", "-region", dest="region", help="AWS region to use", default = REGION)

    return cli_parser

def show_help(parser, msg = None):
    if msg is not None:
        print msg
        print

    parser.print_help()

if __name__ == "__main__":

    parser = get_argparse()
    args = parser.parse_args()
    input_file = os.path.abspath(args.input_file)

    if args.aws_key is None or len(args.aws_key) == 0:
        show_help(parser, "Invalid AWS Key ID. You must specify valid region argument or in script")
        exit(0)

    if args.aws_secret is None or len(args.aws_secret) == 0:
        show_help(parser, "Invalid AWS Key Secret. You must specify valid key argument or in script")
        exit(0)

    if args.region is None or len(args.region) == 0:
        show_help(parser, "Invalid Region. You must specify valid secret argument or in script")
        exit(0)

    # make sure input file exists and show error if not
    if not os.path.exists(input_file):
        show_help(parser, "Input file does not exists")
        sys.exit(1)

    try:
        upload_dynamo()
    except:
        print os.linesep + LINE_BORDER
        print "Error in processing:"
        print "Exception type: ", sys.exc_info()[0]
        print "Exception value:", sys.exc_info()[1]
        print "Traceback:"
        traceback.print_tb(sys.exc_info()[2], 10)
        print LINE_BORDER