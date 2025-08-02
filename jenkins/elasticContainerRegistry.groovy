#!/bin/groovy

def call(dockerAppName) {
"""
Verifies ECR repo is created and lifecycle policies are attached
"""
    
    verifyRepoResults = verifyRepo(dockerAppName)
    if (verifyRepoResults == 255) {
        println("No ECR repo found named \"${dockerAppName}\"")
        createRepo(dockerAppName)
    }
    createLifecyclePolicies(dockerAppName)

}

def verifyRepo(dockerAppName) {
    try {
        r = sh(script: "aws ecr describe-repositories --repository-names ${dockerAppName}", returnStatus: true)
    } catch (Exception e) {
        println(e)
    }
}

def createRepo(dockerAppName) {
    try {
        r = sh(script: "aws ecr create-repository --repository-name ${dockerAppName} --image-tag-mutability IMMUTABLE", returnStatus: true)
    } catch (Exception e) {
        throw e
    }
    return r
}

def createLifecyclePolicies(dockerAppName) {
    lifecyclePolicies = libraryResource("ecr-lifecycle-policies.json")
    sh(script: "aws ecr put-lifecycle-policy --repository-name ${dockerAppName} --lifecycle-policy-text \'${lifecyclePolicies}\'")
}