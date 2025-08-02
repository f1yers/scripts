#!/bin/groovy
import groovy.json.JsonBuilder
import groovy.json.JsonSlurper

def call(config, project, releaseId, jiraPwd) {

    try {
        latestTag = sh(script: "git describe --abbrev=0", returnStdout: true)
        compareTag = '^'+latestTag
    } catch(Exception e) {
        latestTag = false
        compareTag = ""
        echo "Caught error listing git tags ${latestTag} ${compareTag}"
    }

    def commitMsgList = sh(script: "git log --pretty=format:'%s' origin/main ${compareTag}", returnStdout: true)
    def ticketRegex = ~/([A-Z]+\d?-\d+)+/
    def ticketList = (commitMsgList =~ ticketRegex).findAll()
    println(ticketList.flatten().unique())

    linkTicketMap = [
        "update": [
            "fixVersions": [[
                "add": [
                    "id": "${releaseId}"
                    ]
                ]
            ]
        ]
    ]

    def json = new JsonBuilder(linkTicketMap).toString()
    writeJSON file: 'link.json', json: json

    for (ticket in ticketList.flatten().unique()) {
        if (ticket.split("-")[0] == project) {
            sh(script: 'curl -S -s -u <USERNAME>:$jiraPwd -X PUT --data @link.json -H \'Accept: application/json\' -H \'Content-Type: application/json\'' + " ${config.jiraURL}/rest/api/2/issue/${ticket}", returnStdout: true)
        } else {
            println("Skipping ${ticket} because it's not in ${project}.")
        }
    }
}