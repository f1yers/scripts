import os
from slackclient import SlackClient
import logging
import random
import requests
import json
import sys

logging.basicConfig()

slack_token = os.environ.get("SLACK_API_TOKEN")
sc = SlackClient(slack_token)


def main(msg_type, channel, ts, appname, version, environment):

    link = os.environ.get("BUILD_URL")
    num = os.environ.get("BUILD_NUMBER")
    name = os.environ.get("JOB_BASE_NAME")
    text_msg = "{} Build <{}|#{}>".format(name, link, num)

    happy_emojis = [
        "clap",
        "party",
        "party2",
        "party_parrot",
        "star-struck",
        "muscle",
        "selfie",
        "four_leaf_clover",
        "beers",
        "tada",
        "confetti_ball",
        "100",
        "festiveparty",
        "like",
        "rock2"
    ]

    fields_json = [{
        "title": "Application",
        "value": appname,
        "short": "true"
        },
        {
        "title": "Environment",
        "value": environment,
        "short": "true"
        },
        {
        "title": "Version",
        "value": version,
        "short": "false"
    }]

    base_attachment_json = [{}]

    # Begin actual work
    if msg_type == 'starting':

        print(channel)
        auth_token = os.environ.get("JENKINS_API_TOKEN")
        auth_link_split = link.split('//')
        auth_link = "{}//{}@{}".format(auth_link_split[0],
                                       auth_token,
                                       auth_link_split[1])

        try:
            r = requests.get("{}api/json".format(auth_link))
            r = json.loads(r.text, strict=False)
            blame = r['actions'][1]['causes'][0]['userId']
        except:
            # Supressing any error output here so the API token isn't displayed
            blame = 'Unknown'

        base_attachment_json = [{"footer": "Started by: {}".format(blame)}]
        base_attachment_json[0]['color'] = "#D3D3D3"
        base_attachment_json[0]['text'] = "STARTED: {}".format(text_msg)

        starting_msg = sc.api_call(
            "chat.postMessage",
            channel=channel,
            attachments=base_attachment_json
        )

    elif msg_type == 'started':

        base_attachment_json[0]['color'] = "#0000FF"
        base_attachment_json[0]['text'] = "IN PROGRESS: {}".format(text_msg)
        base_attachment_json[0]['fields'] = fields_json

        started_msg = sc.api_call(
            "chat.postMessage",
            channel=channel,
            attachments=base_attachment_json
        )
        print(started_msg['ts'])

    elif msg_type == 'success':
        base_attachment_json[0]['color'] = "#008000"
        base_attachment_json[0]['text'] = "SUCCESSFUL: {}".format(text_msg)
        base_attachment_json[0]['fields'] = fields_json

        sc.api_call("chat.update",
                    channel=channel,
                    ts=ts,
                    attachments=base_attachment_json)

        sc.api_call("reactions.add",
                    channel=channel,
                    timestamp=ts,
                    name=random.choice(happy_emojis))

    elif msg_type == 'failure':
        base_attachment_json[0]['color'] = "#B22222"
        base_attachment_json[0]['text'] = "FAILED: {}".format(text_msg)
        base_attachment_json[0]['fields'] = fields_json

        sc.api_call("chat.update",
                    channel=channel,
                    ts=ts,
                    attachments=base_attachment_json)

        sc.api_call(
            "chat.postMessage",
            channel=channel,
            text="Attention may be required <!here>"
        )

    else:
        exit("Invalid msg_type provided")


def get_channel_id(channel):

    channel_list = sc.api_call("channels.list")
    for c in channel_list['channels']:
        if c['name'] == channel[1:]:
            return c['id']


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(
        description='Sends a formatted message to slack')
    parser.add_argument('--msg_type',
                        help='starting, started, success, failure')
    parser.add_argument('--channel', help='channel to send notifications to')
    parser.add_argument('--ts', help='timestamp of message to update')
    parser.add_argument('--appname', help='Application name')
    parser.add_argument('--version', help='Release version')
    parser.add_argument('--environment', help='Environment')
    parser.set_defaults(appname=None, version=None,
                        environment=None, channel=None)
    p = parser.parse_args()

    if p.channel.startswith('#'):
        channel = get_channel_id(p.channel)

    main(p.msg_type, channel, p.ts, p.appname, p.version, p.environment)
