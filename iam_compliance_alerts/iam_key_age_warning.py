#!/usr/bin/env python3
# pylint: disable=C0103

import argparse
import datetime
import smtplib
from email.message import EmailMessage

import boto3


parser = argparse.ArgumentParser()
parser.add_argument('days', type=int, help="max key age in days")
parser.add_argument('-e', dest='email', action='store_true', help="enable email warning")
parser.add_argument('--email-to', dest='email_to', default="change.me@aoeu.com",
    help="default warning rcpt address")
parser.add_argument('--email-from', dest='email_from', default="no-reply@aoeu.com",
    help="default warning from address")
parser.add_argument('--debug', action='store_true')
parser.add_argument('-v', dest='verbose', action='store_true', help="verbosity")

args = parser.parse_args()

verboseprint = print if args.verbose else lambda *a, **k: None

def key_age_warning(username, key_id, key_age):
    verboseprint(f"key (id: {key_id}) age ({key_age} days) for {username} is older than {args.days}")
    #verboseprint(f"emailing them a warning at {email}")
    #set default email_to
    email_to  = args.email_to

    #get the user tags
    user_tags = client.list_user_tags(UserName=username)
    
    try:
        tag = next((tag for tag in user_tags['Tags'] if tag["Key"].lower() == "email"), None)
        if tag:
            verboseprint(f"found {tag['Key']} : {tag['Value']}")
            email_to = tag['Value']
    except KeyError:
        print(f"no tag found for {username}")


    if args.email:
        msg = EmailMessage()
        msg.set_content(f"key (id: {key_id}) age ({key_age} days) for {username} is older than {args.days}")
        msg['Subject'] = 'Your AWS IAM Access Key has aged'
        msg['From'] = args.email_from
        msg['To'] = email_to

        try:
            s = smtplib.SMTP('localhost')
            s.send_message(msg)
            s.quit()
        except Exception as e:
            print(f"Could not send email: {e}")


client = boto3.client('iam')

response = client.list_users(
    PathPrefix='/',
    # Marker='string',
    # MaxItems=123
)

users = []
today = datetime.datetime.now()


for r in response['Users']:

    response = client.list_access_keys(
        UserName = r['UserName'],
    )
    for key_data in response['AccessKeyMetadata']:
        if key_data['Status'] == 'Active':
            delta = today - key_data['CreateDate'].replace(tzinfo=None)
            if delta.days > args.days:
                key_age_warning(r['UserName'], key_data['AccessKeyId'], key_age=delta.days)
                