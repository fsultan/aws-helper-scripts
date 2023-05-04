#!/usr/bin/env python 

import boto3
import argparse
#import pprint
from datetime import datetime, timedelta

client = boto3.client('inspector')

parser = argparse.ArgumentParser()
parser.add_argument('--at-arn',
        help='assessment template arn')
parser.add_argument('--env',
        choices=["Development", "QA", "UAT", "Production", "SySOps"],
        help="the environment to filter on")
parser.add_argument('--il', type=int, default = 999,
        help="instance limit")
parser.add_argument('--fl', type=int, default = 99999,
        help="findings limit")        
args = parser.parse_args()
#args.ttl = int(args.ttl)

run_start_range_begin = datetime.now() - timedelta (days=14)
run_start_range_end = datetime.now()

instance_limit = args.il
findings_limit = args.fl
instances = {}

def describe_findings(findings_arns):
    response = client.describe_findings(findingArns=findings_arns)
    instance_count = 0
    for finding in response["findings"]:
        agent_id = finding["assetAttributes"]["agentId"]
        if instances.get(agent_id):
            instances[agent_id]["finding_ids"].append(finding["id"])
        else:
            tags = finding["assetAttributes"]["tags"]
            if tags:
                #print(tags)
                instance_name = \
                    list(filter(lambda tag: tag['key'] == 'Name', tags))[0]["value"]
                instance_environment = \
                    list(filter(lambda tag: tag['key'] == 'Environment', tags))[0]["value"]
                instance_customer = \
                    list(filter(lambda tag: tag['key'] == 'Customer', tags))[0]["value"]
            if args.env and args.env != instance_environment:
                break
            instances[agent_id] = {
                "instance_id": finding["assetAttributes"]["agentId"],
                "hostname": finding["assetAttributes"]["hostname"],
                "finding_ids": [finding["id"]],
                "name": instance_name,
                "environment": instance_environment,
                "customer": instance_customer
            }

        instance_count += 1
        if instance_count >= instance_limit:
            break


def get_findings(assessment_run_arn):
    list_findings_args = {
        "assessmentRunArns":[assessment_run_arn],
        "filter": { 
            'severities': [
                'High',
            ],
        },
        "maxResults":20
    }
    findings_count = 0
    while True:
        response = client.list_findings(**list_findings_args)
        #print(response)
        print("Findings Count: ", findings_count)
        # for arn in response["findingArns"]:
        #     print(arn)
        #     print("--- --- ---")
        describe_findings(response["findingArns"])

        if 'nextToken' in response:
            list_findings_args['nextToken'] = response["nextToken"]
        else:
            break
        findings_count += 1
        if findings_count >= findings_limit:
            break

#
#   main
#

assessment_template_arn = args.at_arn

#get the recent assesment run arns
response = client.list_assessment_runs(
    assessmentTemplateArns=[
        assessment_template_arn,
    ],
    filter={
        'startTimeRange': {
            'beginDate': run_start_range_begin,
            'endDate': run_start_range_end
        }
    },
#    maxResults=1
)

assessment_run_arn = response["assessmentRunArns"][0]

#populate the instance list
get_findings(assessment_run_arn)

for k,v in instances.items():
    print("{0},{1},{2},{3},{4}".format(
        v["instance_id"],v.get("name"),v.get("environment"),
        v.get("customer"),len(v["finding_ids"]))
    )
