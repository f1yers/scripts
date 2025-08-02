import os
import boto3
import time

host_name = os.environ['HOSTNAME']
host_ip = os.environ['MY_HOST_IP']

print("The following values will be used to configure DNS:")
print('{}.DOMAIN.com'.format(host_name))
print(host_ip)

client = boto3.client('route53')
client.change_resource_record_sets(
    HostedZoneId='<HOSTED_ZONE_ID>',
    ChangeBatch={
        'Comment': 'Updated IP to {}'.format(host_ip),
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': '{}.DOMAIN.com'.format(host_name),
                    'Type': 'A',
                    'TTL': 0,
                    'ResourceRecords': [
                        {
                            'Value': host_ip
                        }
                    ]
                }
            }
        ]
    }
)

time.sleep(15)