#!/bin/groovy

def call(config) {

    println("Setting version to: ${config.version}")

    if (config.appType == 'java') {
        container("java-${config.javaVersion}") {
            env.CODEARTIFACT_AUTH_TOKEN = doBuild.caAuth("900")
            sh "mvn versions:set -DnewVersion=${config.version}"
        }
    }

    if (config.appType == 'python') {
        sh "sed -i -E 's~(version=\")(.+)(\")~\\1${config.version}\\3~g' setup.py"
        sh "head setup.py"
    }

    if (config.appType == 'nodejs') {
        container("nodejs-${config.nodeVersion}") {
            env.CODEARTIFACT_AUTH_TOKEN = doBuild.caAuth("900")
            sh(script: "yarn version --new-version ${config.version} --no-git-tag-version", returnStdout: true)
        }
    }
}