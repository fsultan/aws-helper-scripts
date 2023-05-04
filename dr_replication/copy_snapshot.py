#!/usr/bin/env python

import argparse
import boto3
import sys
import datetime
import logging
import time
import config

#logging.basicConfig(
    #format='%(levelname)s:%(name)s:%(asctime)s:' + sys.argv[0] + ':%(message)s',
    #filename = config['snap_log'],
    #level=logging.INFO
#)

REGION_CHOICES=['us-east-1','us-east-2','eu-west-1', 'eu-north-1','ap-southeast-2','ap-northeast-2']

parser = argparse.ArgumentParser()
#parser.add_argument('env',
        #choices=["Demo", "Development", "QA", "UAT", "Production", "Infrastructure"],
        #help="the environment to snapshot")
#parser.add_argument('src_region', help='source region', choices=REGION_CHOICES)
#parser.add_argument('dst_region', help='destination region', choices=REGION_CHOICES)
parser.add_argument('region', help='source/connection region', choices=REGION_CHOICES)
parser.add_argument('--volume-id',help='Volume ID to replicate')
parser.add_argument('--ttl',
        help='time to live in days (default: 2 weeks)', default=14)
args = parser.parse_args()
args.ttl = int(args.ttl)

dr_region_map = {
    "us-east-1" : "us-east-2",
    "eu-west-1" : "eu-north-1",
    "ap-southeast-2" : "ap-northeast-1"
    }

expires = (datetime.datetime.now() + datetime.timedelta(days=args.ttl)).strftime('%Y-%m-%dT%H:%M:%S')

#conn = boto.ec2.connect_to_region(ec2_region_name, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
#aws_access_key = config['aws_access_key']
#aws_secret_key = config['aws_secret_key']
src_region = args.region  #config['ec2_region_name']
dst_region = dr_region_map[src_region]

#kms_client = boto3.client('kms', region_name=dst_region)
kms_client_src = boto3.client('kms', region_name=src_region)
kms_client_dst = boto3.client('kms', region_name=dst_region)

#response = client.describe_key(KeyId='alias/%s' % args.,)

client = boto3.client('ec2', region_name=src_region )#, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
#EC2src = boto3.resource('ec2', region_name=src_region)
EC2dst = boto3.resource('ec2', region_name=dst_region)

volumes = []

if args.volume_id:
    volumes = [{"VolumeId": args.volume_id}]
else:
    response = client.describe_volumes(
        Filters=[
            {
                'Name': 'tag:Clone2DR',
                'Values': ['True',]
            },
        ],
    )
    volumes = response['Volumes']

for volume in volumes:
    response = client.describe_snapshots(
        Filters=[{
                'Name': 'volume-id',
                'Values': [volume['VolumeId']]},],
    )
    described_snapshots = response['Snapshots']
    
    sorted_snapshots = sorted(described_snapshots, key=lambda snapshot: snapshot['StartTime']) 
    snapshot = sorted_snapshots[0]
    print("latest snapshot for vol: %s is %s" % (volume['VolumeId'], sorted_snapshots[0]['SnapshotId']))
    
    snapshot_copy_args = {
        'Description': "Copied from region %s" % src_region,
        'SourceRegion': src_region,
        #'DestinationRegion': dst_region,  #not valid for this type of request ?
        }
    
    #if the snapshot is encrypted, get the corresponding key used in the DR region
    if snapshot['Encrypted']:
        snapshot_copy_args['Encrypted'] = True
        
        response = kms_client_src.describe_key(KeyId=snapshot['KmsKeyId'])
        kms_src = response['KeyMetadata']
        #set the dr key if custom
        if kms_src['KeyManager']!='AWS':
            response = kms_client_src.list_aliases() 
            dst_kms_alias = ''
            for alias in response['Aliases']:
                if alias['TargetKeyId']==kms_src['KeyId']:
                    dst_kms_alias = alias['AliasName']
                    break
                
            response = kms_client_dst.describe_key(KeyId=dst_kms_alias)
            snapshot_copy_args['KmsKeyId'] = response['KeyMetadata']['KeyId']
    print("Snapshot copy args:")
    print(snapshot_copy_args)
    
    #connect to the dst api endpoint to copy the snapshot over
    response = EC2dst.Snapshot(sorted_snapshots[0]['SnapshotId']).copy(**snapshot_copy_args) 
    print(response)
    snapshot_id_dst = response['SnapshotId']
    snapshot_dst = EC2dst.Snapshot(snapshot_id_dst)
    
    tag = snapshot_dst.create_tags(
        Tags = snapshot['Tags']
    )
    