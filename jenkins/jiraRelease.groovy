#!/bin/groovy
import groovy.json.JsonBuilder
import groovy.json.JsonSlurper

def search(config, project, jiraPwd) {

    r = sh(script: 'curl -S -s -u <USERNAME>:$jiraPwd -X GET -H \'Accept: application/json\'' + " ${config.jiraURL}/rest/api/2/project/${project}/version?maxResults=9999", returnStdout: true)
    JsonSlurper slurper = new JsonSlurper()
    Map parsedJson = slurper.parseText(r)
    def existingIdJson = parsedJson.values.findAll{it.name == "${config.appName} - ${config.version}"}

    if (existingIdJson[0]) {
        return existingIdJson[0].id
    }
}

def create(config, project, jiraPwd) {

    def createMap = [
        "name": "${config.appName} - ${config.version}",
        "description": "${config.jiraTicketNum} - ${config.appName} - ${config.version}",
        "userReleaseDate": "",
        "project": "${project}",
        "archived": "false",
        "released": "false"
    ]
    def json = new JsonBuilder(createMap).toString()
    writeJSON file: 'create.json', json: json

    r = sh(script: 'curl -S -s -u <USERNAME>:$jiraPwd -X POST --data @create.json -H \'Accept: application/json\' -H \'Content-Type: application/json\'' + " ${config.jiraURL}/rest/api/2/version", returnStdout: true)
    JsonSlurper slurper = new JsonSlurper()
    Map parsedJson = slurper.parseText(r)

    return parsedJson.id
}

def released(config, releaseId, jiraPwd) {

    def now = new Date()

    releasedMap = [
        "id": releaseId,
        "released": "true",
        "releaseDate": now.format("yyyy-MM-dd").toString()
    ]
    def json = new JsonBuilder(releasedMap).toString()
    writeJSON file: 'released.json', json: json
    r = sh(script: 'curl -S -s -u <USERNAME>:$jiraPwd -X PUT --data @released.json -H \'Accept: application/json\' -H \'Content-Type: application/json\'' + " ${config.jiraURL}/rest/api/2/version/${releaseId}", returnStdout: true)
}