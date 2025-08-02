#!/bin/groovy
import groovy.json.JsonSlurper


def purgeCache() {
"""

"""
    withCredentials([string(credentialsId: 'cloudflare-auth', variable: 'cloudFlareToken')]) {
        r = sh(script: "curl -X POST \
                        -H \'Authorization: Bearer $cloudFlareToken\' \
                        -H \'Content-Type: application/json\' \
                        https://api.cloudflare.com/client/v4/zones/<ID>/purge_cache \
                        --data \'{\"purge_everything\": true}\'", returnStdout: true)
    }


    JsonSlurper slurper = new JsonSlurper()
    Map parsedJson = slurper.parseText(r)
    print(parsedJson)

    if (parsedJson.success == true) {
        return
    } else {
        error "Something went wrong clearing the cloudflare cache"
    }
}