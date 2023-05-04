#!/usr/bin/env python3
# pylint: disable=C0103

import argparse
import datetime
import smtplib
from email.message import EmailMessage

import boto3


parser = argparse.ArgumentParser()
parser.add_argument('days', type=int, help="days since last activity")
parser.add_argument('-e', dest='email', action='store_true', help="enable email warning")
parser.add_argument('--email-to', dest='email_to', default="change.me@aoeu.com",
    help="default warning rcpt address")
parser.add_argument('--email-from', dest='email_from', default="no-reply@aoeu.com",
    help="default warning from address")
parser.add_argument('--debug', action='store_true')
parser.add_argument('-v', dest='verbose', action='store_true', help="verbosity")

args = parser.parse_args()

verboseprint = print if args.verbose else lambda *a, **k: None

#client = boto3.client("sts")
account_id = boto3.client("sts").get_caller_identity()["Account"]
account_alias = boto3.client('iam').list_account_aliases()['AccountAliases'][0]

client = boto3.client('iam')

r_users = client.list_users(
    PathPrefix='/',
    # Marker='string',
    # MaxItems=123
)

inactive_users = []
today = datetime.datetime.now()

for r in r_users['Users']:
    #print(f"checking {r}")
    active = False #assume inactive until proved otherwize
    try:
        passwd_delta = today - r['PasswordLastUsed'].replace(tzinfo=None)
    except KeyError:
        #never logged in apparently
        verboseprint(f"user {r['UserName']} never logged in...")

        passwd_delta = None

    if passwd_delta and passwd_delta.days <= args.days:
        active = True
    else: 
        #user seems inactive, check key age
        verboseprint("  checking key data ....")
        r_access_keys = client.list_access_keys(
            UserName = r['UserName'],
        )
        for key_data in r_access_keys['AccessKeyMetadata']:
            #print(key_data)
            if key_data['Status'] == 'Active':
                response = client.get_access_key_last_used(
                    AccessKeyId=key_data['AccessKeyId']
                )
                try:
                    delta = today - response['AccessKeyLastUsed']['LastUsedDate'].replace(tzinfo=None)
                except KeyError:
                    #key never used but there may be others
                    pass
                else:
                    if delta.days < args.days:
                        #user confirmed active
                        active = True

    if not active:
        verboseprint(f"user {r['UserName']} no recently used key found...")
        inactive_users.append(r['UserName'])

print("inactive users:")
print(inactive_users)

if args.email:
    msg = EmailMessage()
    msg.set_content(f"AWS Inactive Users Report for {account_alias} - {account_id}:\n accounts stale for more than {args.days}\n{inactive_users}")
    msg['Subject'] = f"AWS Inactive Users Report for {account_alias}"
    msg['From'] = args.email_from
    msg['To'] = args.email_to

    try:
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
    except Exception as e:
        print(f"Could not send email: {e}")