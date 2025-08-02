import json
import sys
import requests
import os


def jira_comment(ticket, version, build_type, build_link):

    if build_type == 'release':
        title = "Release Build"
        description = "Release version {} has been built".format(version)
        titleBGColor = "98AFC7"
        bgColor = "DEF5FF"
    if build_type == 'preprod':
        title = "PreProd Deployment"
        description = "Release version {} has been deployed to PreProduction".format(version)
        titleBGColor = "B5EAAA"
        bgColor = "FBFFF0"
    if build_type == 'uat':
        approver = get_approver(ticket)
        title = "UAT Deployment"
        description = """Release version {0} has been deployed to UAT
        Approved By: {1}
        """.format(version, approver)
        titleBGColor = "F9966B"
        bgColor = "FFFFE3"
    if build_type == 'production':
        approver = get_approver(ticket)
        title = "Production Deployment"
        description = """Release version {0} has been deployed to Production
        Approved By: {1}
        """.format(version, approver)
        titleBGColor = "F9966B"
        bgColor = "FFFFE3"
    if build_type == 'closeout':
        title = "Version closeout"
        description = "This version has been marked as complete"
        titleBGColor = "D7D7BE"
        bgColor = "F5F5DC"

    method = 'post'
    url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}/comment".format(ticket)
    comment_body = """
    {{panel:title={0}|borderStyle=dashed|borderColor=#ccc|titleBGColor=#{1}|bgColor=#{2}}}
    {3}
    [*Jenkins Build*|{4}]
    {{panel}}
    """.format(title, titleBGColor, bgColor, description, build_link)

    comment_body_json = {
        "body": ""
    }

    comment_body_json['body'] = comment_body
    payload = json.dumps(comment_body_json)
    make_request(url, method, payload)
    transistion_issue(ticket, build_type)


def transistion_issue(ticket, build_type):

    method = 'get'
    url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}".format(ticket)
    ticket_json = make_request(url, method, payload=None)
    ticket_json = json.loads(ticket_json[0])
    current_status = ticket_json['fields']['status']['name']
    print("Current status is: " + current_status)

    transistion_json = {
        "transition": {
            "id": ""
        }
    }

    method = 'post'
    url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}/transitions".format(ticket)

    if current_status != "Open" and build_type == "release":
        transistion_json['transition']['id'] = "11"
        print("Current status is {}. Moving ticket back to Open!".format(current_status))
    elif current_status == "Open" and build_type == "preprod":
        transistion_json['transition']['id'] = "21"
    elif current_status == "Open" and build_type == "closeout":
        transistion_json['transition']['id'] = "41"
    elif current_status == "Deployed to PreProd" and build_type == "closeout":
        transistion_json['transition']['id'] = "41"
    elif current_status == "Approved for Production" and build_type == "production":
        transistion_json['transition']['id'] = "61"
    elif current_status == "Deployed to Production" and build_type == "closeout":
        transistion_json['transition']['id'] = "41"
    else:
        print("Not required to move ticket to another status, exiting.")
        sys.exit(0)

    payload = json.dumps(transistion_json)
    make_request(url, method, payload)


def get_approver(ticket):

    url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}?expand=changelog".format(ticket)
    method = 'get'
    results = make_request(url, method, payload=None)
    data = json.loads(results[0])
    for log in data['changelog']['histories']:
        for item in log['items']:
            if item['field'] == "status":
                if item['toString'] == "Approved for Production":
                    approver = log['author']['displayName']

    return approver


def make_request(url, method, payload):

    headers = {'content-type': 'application/json'}
    auth = (os.environ.get('JIRAUSERNAME', '@@JIRAUSERNAME@@'),
            os.environ.get('JIRAPASSWORD', '@@JIRAPASSWORD@@'))

    try:
        if method == 'post':
            r = requests.post(url, payload, headers=headers, auth=auth)
        else:
            r = requests.get(url, headers=headers, auth=auth)
    except requests.exceptions.HTTPError as e:
        print("An error occurred when making the request", e.message)

    return r.text, r.status_code


if __name__ == "__main__":

    jira_comment(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
  