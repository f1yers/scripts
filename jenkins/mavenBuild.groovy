#!/bin/groovy

def call(config) {
"""

"""
    container("java-${config.javaVersion}") {
        env.CODEARTIFACT_AUTH_TOKEN = doBuild.caAuth("3600")
        sh "mvn clean deploy -s /usr/share/maven/conf/settings.xml"
    }
}