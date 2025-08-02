#!/bin/groovy

def call(List apps, String environment) {
"""
Asynchronously start scaled down apps and waits for them all to be available
"""

    helmDeploy.getKubeConfig(envDefaults(environment).kubeContext)
    echo "Starting scale up in ${environment} for the following apps: ${apps}"

    def scaleApps = apps.collectEntries { app ->
        ["${app}": {
            echo app
            helmAppValues = helmDeploy.getValues("${WORKSPACE}/kubernetes/helm/values/${environment}/${app}.yaml")
            try {
                def appHost       = helmAppValues.ingressRules[0].host
                def appContext    = helmAppValues.ingressRules[0].http.paths[0].path

                echo "Host: " + appHost
                echo "Context: " + appContext

                def contextRegex = ~/^([^(]*)(.*)/
                def context = createMatcher(appContext, contextRegex)
                if (context == '/') { context = '' } // remove dup slash
                sh "curl -s -o /dev/null \
                    https://${appHost}${context}/startplz"
            } catch(java.lang.NullPointerException e) {
                echo "Please update the helm value to include an endpoint for scaling. \n" + e
            } catch(hudson.AbortException e) {
                echo "DNS may not be configured properly. \n" + e
            } catch(Exception e) {
                echo e
            }

            // Verify each deployment has replicas that are ready
            def int readyReplicas = 0
            def int attempts = 0
            while (readyReplicas < 1) {
                helmAppValues = helmDeploy.getValues("${WORKSPACE}/kubernetes/helm/values/${environment}/${app}.yaml")
                if (helmAppValues.replicaCount == 0) {
                    break
                }
                namespace = helmAppValues.namespace
                kind = helmAppValues.kind ?: "deployment"
                appName = helmAppValues.appName ?: app
                output = sh(script: "kubectl get ${kind} -n ${namespace} ${appName} -o yaml --kubeconfig ${WORKSPACE}/eks.conf", returnStdout: true).trim()

                if ((output.readLines().find { it.contains('readyReplicas') }?.split(':')?.getAt(1)?.trim() as Integer ?: 0) >= 1) {
                    echo "Deployment has been scaled up completely and is ready"
                    readyReplicas++
                } else {
                    if (attempts >= 40) {
                        error "Scaling of ${appName} failed."
                    }
                    attempts++
                    echo "Waiting 30 seconds for app to be ready..."
                    sleep(30)
                }
            }
        }]
    }
    parallel scaleApps
}

@NonCPS
def createMatcher(appContext, contextRegex) {
    def matcher = (appContext =~ contextRegex)
    matcher ? matcher[0][1] : "noMatchError"
}