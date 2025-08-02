#!/bin/groovy
import groovy.json.JsonBuilder
import groovy.json.JsonSlurper


def call(Map config) {
    // In order to interact with dataflow you must have an Okta token
    def token = okta.getToken(config, scope="dataflow-view dataflow-deploy dataflow-destroy dataflow-manage dataflow-modify dataflow-schedule dataflow-create")

    // does the application version exist?
    // def appExists = getApp(config, token)

    // attempt to register application with the Dataflow server
    registerAppWithVersion(config, token)

    if (config.dataflow.setDefaultVersion) {
        setDefaultVersion(config, token)
    }

    if (config.dataflow.deployStream) {
        // there could be multiple streams in the definitions.json
        def definitions = readJSON file: config.dataflow.definitions
        println("Starting stream loop")
        definitions.entrySet().each { entry ->
            def streamName = entry.key
            def streamDef = entry.value

            println "Name: ${streamName}, Definition: ${streamDef}"

            // does the stream exist?
            // streamExists = validateStream(streamName, config, token)

            deleteStream(streamName, config, token)
            createStream(streamName, streamDef, config, token)

            // deploy the new streams
        }
    }
}

def getApp(config, token) {

    r = jenkinsUtils.hideCmd("curl -s \
                    -H \'Authorization: Bearer ${token}\' \
                    -H \'Accept: application/json\' \
                    ${config.dataflow.url}/apps?search=${config.appName}&type=${config.dataflow.type}")

    JsonSlurper slurper = new JsonSlurper()
    Map parsedJson = slurper.parseText(r)

    if (parsedJson.page.totalElements > 0) {
        println("Found existing elements for ${config.appName}")
        return true
    }
    return false
}

def registerAppWithVersion(config, token) {

    r = jenkinsUtils.hideCmd("curl -X POST -s \
                            -H \'Authorization: Bearer ${token}\' \
                            -H \'Accept: application/json\' \
                            -H \'Content-Type: application/x-www-form-urlencoded\' \
                            ${config.dataflow.url}/apps/${config.dataflow.type}/${config.appName}/${config.dockerTag} \
                            --data \'uri=docker://${config.dockerURL}/${config.appName}:${config.dockerTag}\'")
    try {
        
        println("registerAppWithVersion() returned " + r)
        if (!r.trim()) {
            println("App registration was successful")
            return
        }

        JsonSlurper slurper = new JsonSlurper()
        Map parsedJson = slurper.parseText(r)

        if (parsedJson._embedded?.errors) {
            if (parsedJson._embedded.errors[0].logref == 'AppAlreadyRegisteredException') {
                println("App version already registered with Dataflow")
                return
            }
            println("There may have been an issue registering the app, continuing for now " + parsedJson._embedded.errors)
        }
    } catch(hudson.AbortException e) {
        def exit_6 = (e.message =~ /exit code 6/).find()
            if(exit_6) {
                throw new Exception("Received exit code 6 - This could be a DNS issue.")
            }
    } catch(Exception e) {
        throw new Exception("Issue registering application with the Dataflow server.\n " + e)
    }
}

def setDefaultVersion(config, token) {

    r = jenkinsUtils.hideCmd("curl -X PUT -s \
                    -H \'Authorization: Bearer ${token}\' \
                    -H \'Accept: application/json\' \
                    ${config.dataflow.url}/apps/${config.dataflow.type}/${config.appName}/${config.dockerTag}")

    try {
        println("setDefaultVersion() returned " + r)
        if (!r.trim()) {
            println("A new default version was set successfully")
            return
        }

        JsonSlurper slurper = new JsonSlurper()
        Map parsedJson = slurper.parseText(r)

        if (parsedJson._embedded?.errors) {
            println("There may have been an issue setting the default version, continuing for now " + parsedJson._embedded.errors)
        }
    } catch(Exception e) {
        throw new Exception("Issue setting default version\n " + e)
    }
}

def validateStream(streamName, config, token) {
    /*
    returns true if the stream validates
    returns false if the stream does not exist/does not validate
    */
    r = jenkinsUtils.hideCmd("curl -s \
                    -H \'Authorization: Bearer ${token}\' \
                    -H \'Accept: application/json\' \
                    ${config.dataflow.url}/streams/validation/${streamName}")

    try {
        println("validateStream() returned: "+ r)
        if (!r.trim()) {
            println("Validation suceeded for stream ${streamName}")
            return true
        }

        JsonSlurper slurper = new JsonSlurper()
        Map parsedJson = slurper.parseText(r)

        if (parsedJson._embedded?.errors) {
            if (parsedJson._embedded.errors[0].logref == 'NoSuchStreamDefinitionException') {
                println("Definition does not exist")
                return false
            }
            throw new Exception("Failed to validate stream\n" + parsedJson._embedded.errors)
        }
    } catch(Exception e) {
        throw new Exception("Something went wrong when validating stream\n" + e)
    }
}

def createStream(streamName, streamDef, config, token) {

    println("Attempting to create stream ${streamName} with the following definitions:\n\t" + streamDef)
    r = jenkinsUtils.hideCmd("curl -X POST -s \
                    -H \'Authorization: Bearer ${token}\' \
                    -H \'Accept: application/json\' \
                    -H \'Content-Type: application/x-www-form-urlencoded\' \
                    ${config.dataflow.url}/streams/definitions \
                    --data \'name=${streamName}&definition=${streamDef}\'")
    try {
        println("createStream() returned: "+ r)
        if (!r.trim()) {
            println("${streamName} created successfully.")
            return true
        }
        JsonSlurper slurper = new JsonSlurper()
        Map parsedJson = slurper.parseText(r)

        if (parsedJson._embedded?.errors) {
            if (parsedJson._embedded.errors[0].logref == 'DuplicateStreamDefinitionException') {
                println("Stream ${streamName} already exists.  Call deleteStream() first.")
                return false
            }
            throw new Exception("Failed to create stream\n" + parsedJson._embedded.errors)
        }
    } catch(Exception e) {
        throw new Exception("Something went wrong when creating ${streamName}\n" + e)
    }

}

def deleteStream(streamName, config, token) {

    println("Attempting to delete stream ${streamName}")
    try {
        r = jenkinsUtils.hideCmd("curl -X DELETE -s \
                        -H \'Authorization: Bearer ${token}\' \
                        -H \'Accept: application/json\' \
                        ${config.dataflow.url}/streams/definitions/${streamName}")
    } catch(Exception e) {
        throw new Exception("Something went wrong when deleting ${streamName} \n" + e)
    }
}
