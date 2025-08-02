#!/bin/groovy

def call(config) {
    podTemplate(yaml: libraryResource("build-tools.yaml")) {
        node(POD_LABEL) {

            gitRepo.configure()

            checkout scm
            gitRepo.checkOutDevOps(config)

            container('build-tools') {
                try {
                    stage('Initialize') {
                        withCredentials([string(credentialsId: 'jira-auth', variable: 'jiraPwd')]) {
                            buildConfig(config, jiraPwd)

                            if (config.envName == 'production') {
                                jiraTicket.getApproval(config, jiraPwd)
                            }
                        }
                    }

                    if (config.build) {
                        stage('Sonar Analysis') {
                            sonarScan(config)
                        }

                        if (config.appSubType == 'library') {
                            if (config.appType == 'java') {
                                stage('Maven Build') {
                                    mavenBuild(config)
                                }
                            }
                        } else {
                            stage('Kaniko Build') {
                                kanikoBuild(config)
                            }
                        }

                        if (config.envName == 'preprod') {
                            stage('Version Bump') {
                                gitRepo.pushVersion(config)
                            }
                        }
                    }

                    if (config.deploy) {
                        stage('Deploy') {
                            println("Deploying ${config.appName}:${config.version}")
                            if (config.appSubType == 'integration') {
                                dataflow(config)
                            } else {
                                helmDeploy(config)
                            }
                        }

                        if (config.runPurgeCache) {
                            stage('Purge Cache') {
                                cloudFlare.purgeCache()
                            }
                        }
                    }

                    stage('Post Build Steps') {
                        withCredentials([string(credentialsId: 'jira-auth', variable: 'jiraPwd')]) {
                            postBuild(config, jiraPwd)
                        }
                    }

                } catch(Exception e) {
                    stage('Failure') {
                        throw e
                    }

                } finally {
                    config.envDefaults.transistionId = '41'
                    withCredentials([string(credentialsId: 'jira-auth', variable: 'jiraPwd')]) {
                        jiraTicket.transistion(config, jiraPwd)
                    }
                }
            }
        }
    }
}