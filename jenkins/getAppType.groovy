#!/bin/groovy

def call() {
    try {
        if (fileExists('pom.xml')){
            println('Found java app')
            appType = 'java'
            return appType
        }

        if (fileExists('setup.py')){
            println('Found python app')
            appType = 'python'
            return appType
        }

        if (fileExists('.ruby-version')){
            println('Found ruby app')
            appType = 'ruby'
            return appType
        }

        if (fileExists('package.json')){
            println('Found nodejs app')
            appType = 'nodejs'
            return appType
        }
    } catch (Exception e) {
        throw 'Could not find appType'
    }
}