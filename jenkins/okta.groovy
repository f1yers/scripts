#!/bin/groovy
import groovy.json.JsonBuilder
import groovy.json.JsonSlurper


def getToken(Map config,
             String grantType = "client_credentials",
             String scope) {
    /* https://developer.okta.com/docs/reference/api/oidc/#token */
    println("Getting access token using credId: ${config.dataflow.credId}")
    withCredentials([string(credentialsId: config.dataflow.credId, variable: 'clientCreds')])
    {
        r = jenkinsUtils.hideCmd("curl -X POST -s \
                        -H \'Authorization: Basic $clientCreds\' \
                        -H \'Accept: application/json\' \
                        -H \'Content-Type: application/x-www-form-urlencoded\' \
                        ${config.envDefaults.oktaOrgUrl}/oauth2/default/v1/token \
                        --data \'grant_type=${grantType}&scope=${scope}\'")
    }

    JsonSlurper slurper = new JsonSlurper()
    Map parsedJson = slurper.parseText(r)

    return parsedJson["access_token"]
}
