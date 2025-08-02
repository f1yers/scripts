#!/bin/groovy
import groovy.json.JsonSlurper


def call(config) {
"""
Returns true if pipeline should build application
"""

    if (config.appSubType == 'library') {
        println("Running build stage for: ${config.version}")
        return true // If it's a library, build it.
    } else {
        // Only check for ECR setup if it's not a library
        env.ECR_AUTH_TOKEN = ecrAuth()
        elasticContainerRegistry(config.dockerAppName)
    }

    if (imageExists(config)) {
        return false // If the image exists, don't build.
    }

    println("Called doBuild, returning environment default")
    return config.envDefaults.build
}

def imageExists(config) {
"""
Calls docker registry to see if image tag already exists
"""

    r = sh(script: "aws ecr describe-images --repository-name ${config.appName} --query 'sort_by(imageDetails,& imagePushedAt)[*].imageTags[0]'", returnStdout: true)
    def imageList = new JsonSlurper().parseText(r)
    return imageList.any { config.dockerTag == it }
}

def caAuth(tokenTTL) {
"""
    Provisions a token for codeartifact for the specified TTL
"""
    container('build-tools') {
        def authToken = sh(script: "aws codeartifact get-authorization-token --duration-seconds ${tokenTTL} --domain mbopartners --domain-owner 596212449348 --query authorizationToken --output text", returnStdout: true)
        return authToken
    }
}

def ecrAuth() {
"""
    Provisions a token for ECR using awscli
"""
    container('build-tools') {
        def authToken = sh(script: "aws ecr get-authorization-token --output text --query 'authorizationData[].authorizationToken'", returnStdout: true)
        return authToken
    }
}