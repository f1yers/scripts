#!/bin/groovy


def putFiles(accessToken, siteId, folderPath, fileName) {

    echo "Syncing ${fileName} to Sharepoint path ${folderPath}"
    jenkinsUtils.hideCmd("curl -s -X PUT \
                -H \'Authorization: Bearer $accessToken\' \
                -H \'Content-Type: application/json\' \
                https://graph.microsoft.com/v1.0/sites/${siteId}/drive/root:${folderPath}:/children/${fileName}/content \
                --data @${fileName}")
}

def listFiles(accessToken, siteId, folderPath) {

    // List files using the REST API
    r = jenkinsUtils.hideCmd("curl -s \
                    -H \'Authorization: Bearer $accessToken\' \
                    -H \'Content-Type: application/json\' \
                    https://graph.microsoft.com/v1.0/sites/${siteId}/drive/root:${folderPath}:/children")

    // Parse the JSON response
    json = readJSON text: r
    json.value.each { f ->
        echo f.name
    }
}

def getAccessToken(username, password, sharepointSiteUrl, directoryId, applicationId, clientSecret) {

    tokenUrl = "https://login.microsoftonline.com/${directoryId}/oauth2/v2.0/token"

    r = jenkinsUtils.hideCmd("curl -s -X POST \
                    -H \'Content-Type: application/x-www-form-urlencoded\' \
                    $tokenUrl \
                    --data \'client_id=${applicationId}&client_secret=${clientSecret}&scope=https://graph.microsoft.com/.default&grant_type=client_credentials\'")

    json = readJSON text: r

    return json.access_token
}
