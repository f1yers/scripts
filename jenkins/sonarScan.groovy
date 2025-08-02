#!/bin/groovy

def call(Map config) {
"""

"""
    if (config.skipSonar == true) {
        println("Skipping Sonar scanning..")
    } else {
        withSonarQubeEnv('sonar') {
            sh "/usr/local/sonar-scanner/bin/sonar-scanner -Dproject.settings=./sonar-scanner.properties -Dsonar.projectVersion=${config.version}"
        }
    }
}