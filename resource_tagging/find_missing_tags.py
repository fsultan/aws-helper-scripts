#!/usr/bin/env python3

import boto3
import argparse

from botocore.exceptions import ClientError

RESOURCE_CHOICES = [
    "instance",
    "elb",
    "volume",
    "snapshot",
    ]

parser = argparse.ArgumentParser()
parser.add_argument('resource', choices=RESOURCE_CHOICES, help="aws service resource name (boto)")
parser.add_argument('tags', nargs='+', help="list tagName[,tagName]")
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
    tag_names = filter_arg.split(","),
    return tag_names

find_tags = args.tags   

client = boto3.client('ec2')

response = client.describe_instances()
instances_ids = []
for reservation in response.get("Reservations"):
    for instance in reservation.get("Instances"):
        instances_ids.append(instance.get("InstanceId"))

for instance_id in instances_ids:
    response = client.describe_tags(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [
                    instance_id,
                ]
            },
        ],
    )
    print(instance_id)
    print(response['Tags'])


    





