#!/bin/groovy

def call(Map config) {
"""

"""
    container(name: 'kaniko', shell: '/busybox/sh') {
        env.CODEARTIFACT_AUTH_TOKEN = doBuild.caAuth("3600")
        sh """#!/busybox/sh
        /kaniko/executor --context `pwd` --dockerfile ${config.dockerFile} --destination ${config.dockerURL}/${config.dockerAppName}:${config.dockerTag} --build-arg ENV_NAME=${config.envName} --build-arg VERSION=${config.version} --build-arg CODEARTIFACT_AUTH_TOKEN=${CODEARTIFACT_AUTH_TOKEN}
        """
    }
}