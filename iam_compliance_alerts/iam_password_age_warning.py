#!/usr/bin/env python3
# pylint: disable=C0103

import argparse
import datetime
import smtplib
import csv
#import base64

from email.message import EmailMessage

import boto3

parser = argparse.ArgumentParser()
parser.add_argument('days', type=int, help="max password age in days")
parser.add_argument('-e', dest='email', action='store_true', help="enable email warning")
parser.add_argument('--email-to', dest='email_to', default="change.me@aoeu.com",
    help="default warning rcpt address")
parser.add_argument('--email-from', dest='email_from', default="no-reply@aoeu.com",
    help="default warning from address")
parser.add_argument('--debug', action='store_true')
parser.add_argument('-v', dest='verbose', action='store_true', help="verbosity")

args = parser.parse_args()

verboseprint = print if args.verbose else lambda *a, **k: None

client = boto3.client('iam')

response = client.get_credential_report()
#print(response['Content'].decode('utf-8'))

csv_cred_report = response['Content'].decode('utf-8')

line_count = 0
for row in csv_cred_report.splitlines():
    if line_count == 0:
        pass
        line_count += 1
    else:
        sr = row.split(",")
        print(f'user {sr[0]} password last changed {sr[5]}')
        line_count += 1


#csv_cred_report = base64.standard_b64decode(response['Content']).decode('utf-8')  

#print(csv_cred_report)
# users = []
# today = datetime.datetime.now()


# for r in response['Users']:
#     response = client.list_access_keys(
#         UserName = r['UserName'],
#     )
#     for key_data in response['AccessKeyMetadata']:
#         if key_data['Status'] == 'Active':
#             delta = today - key_data['CreateDate'].replace(tzinfo=None)
#             if delta.days > args.days:
#                 key_age_warning(r['UserName'], key_data['AccessKeyId'], key_age=delta.days)
                