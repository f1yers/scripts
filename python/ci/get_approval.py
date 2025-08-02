import json
import sys
import requests
import os


def get_approver(ticket):

    url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}?expand=changelog".format(ticket)
    method = 'get'
    results = make_request(url, method, payload=None)
    data = json.loads(results[0])

    if data['fields']['status']['name'] not in ['Approved for Production', 'Deployed to Production']:
        print("DEPLOYMENT HAS NOT BEEN APPROVED!!!")
        sys.exit(1)

    for log in data['changelog']['histories']:
        for item in log['items']:
            if item['field'] == "status":
                if item['toString'] == "Approved for Production":
                    if log['author']['displayName']:
                        print("Deployment approved by: {}".format(log['author']['displayName']))


def make_request(url, method, payload):

    headers = {'content-type': 'application/json'}
    auth = (os.environ.get('JIRAUSERNAME', '@@JIRAUSERNAME@@'),
            os.environ.get('JIRAPASSWORD', '@@JIRAPASSWORD@@'))

    try:
        r = requests.get(url, headers=headers, auth=auth)
    except requests.exceptions.HTTPError as e:
        print("An error occurred when making the request", e.message)
        sys.exit(1)

    return r.text, r.status_code


if __name__ == "__main__":

    get_approver(sys.argv[1])
