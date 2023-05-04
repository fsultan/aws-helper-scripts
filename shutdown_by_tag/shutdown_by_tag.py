#!/bin/env python

import boto3
import argparse

from botocore.exceptions import ClientError


parser = argparse.ArgumentParser()
parser.add_argument('include', nargs='+', help="list tagName:tagvalue[,tagvalue] pairs")
parser.add_argument('--exclude', nargs='*', help="list tagName:tagvalue[,tagvalue] pairs")
parser.add_argument('--debug', action='store_true')
parser.add_argument('-v', dest='verbose', action='store_true', help="verbosity")

args = parser.parse_args()


standard_filters = [
    {
        'Name': 'instance-state-name',
        'Values': ["running"],
    }
]

def split_filter_args(filter_arg):
    filter = {
        'Name': "tag:"+filter_arg.split(":")[0],
        'Values': [filter_arg.split(":")[1]], #.split(","),        
        }
    return filter

def get_instance_ids(filter):
    if not filter:
        return []
    response = client.describe_instances(
        Filters= [filter] + standard_filters
    )
    instances_ids = []
    for reservation in response.get("Reservations"):
        for instance in reservation.get("Instances"):
            instances_ids.append(instance.get("InstanceId"))
    return instances_ids


client = boto3.client('ec2')

include_filters = [split_filter_args(filter_arg) for filter_arg in args.include if args.include]

exclude_filters = [split_filter_args(filter_arg) for filter_arg in (args.exclude if args.exclude is not None else [])]

#get_instance_ids uses AND with filters, to shutdown on OR logic run this script multiple times
included_instances_ids = []
for include_filter in include_filters:
    included_instances_ids.extend(get_instance_ids(include_filter))
    
excluded_instances_ids = []
for exclude_filter in exclude_filters:
    excluded_instances_ids.extend(get_instance_ids(exclude_filter))
    
actionable_instances = list(set(included_instances_ids) - set(excluded_instances_ids))

if args.verbose:
    print("Included : %s " % included_instances_ids)
    print("Excluded : %s " % excluded_instances_ids)
    print "Actionable Instance IDs : " , actionable_instances

    
print "Shutting Down Instances ...."

ec2 = boto3.resource('ec2')
for instance_id in actionable_instances:
    instance = ec2.Instance(instance_id)
    instance_name = [tag["Value"] for tag in instance.tags if tag['Key'] == 'Name']
    print "Stopping %s" % instance_name[0]
    try:
        response = ec2.Instance(instance_id).stop(DryRun=args.debug)
    except ClientError as e:
        if e.response['Error']['Code'] == 'DryRunOperation':
            print("Request would have succeeded, but DryRun flag is set")
        else:
            print("Unexpected error: %s" % e)        
    except:
        print("Unexpected error")
        raise    