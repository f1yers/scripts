#!/bin/groovy

def call(Map config) {
"""
Deploys app with helm using values from config map
"""
    helmAppValues = getValues("${WORKSPACE}/dev-ops/kubernetes/helm/values/${config.envName}/${config.appName}.yaml")
    getKubeConfig(config.envDefaults.kubeContext)
    sh """helm upgrade -i --wait --timeout ${config.helmTimeout} --set podAnnotations.timestamp="`date`" \
        --set image.fullPath=${config.dockerURL}/${config.dockerAppName}:${config.dockerTag} \
        -f ${WORKSPACE}/dev-ops/kubernetes/helm/values/${config.envName}/${config.appName}.yaml \
        ${config.appName} \
        --namespace ${helmAppValues.namespace} \
        ${WORKSPACE}/dev-ops/kubernetes/helm/charts/app \
        --kubeconfig ${WORKSPACE}/eks.conf"""
}


def getKubeConfig(context) {
"""
Using provided context, download the associated EKS cluster config
"""
    sh "aws eks update-kubeconfig --name ${context} --kubeconfig ${WORKSPACE}/eks.conf"
}

def getValues(file) {
"""
Read and return helm values from dev-ops repo for specified app
"""
    def values = readYaml file: file
    return values
}