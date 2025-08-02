#!/usr/bin/groovy
@Grab('org.yaml:snakeyaml:1.17')
import org.yaml.snakeyaml.Yaml

def workDir = SEED_JOB.getWorkspace()
def config = new Yaml().load(("${workDir}/apps.yaml" as File).text)

println(config)
for (app in config.jobs) {
    def appToken = app.name 
    def appScriptPath = app.scriptPath ?: 'Jenkinsfile'
    def defaultBranch = app.defaultBranch ?: 'main'

    def jobParameters = app.jobParameters ?: "{ -> stringParam('version') }"
    def jobParametersClosure = new GroovyShell().evaluate(jobParameters)

    def appCronTrigger = app.cronTrigger ?: ""
    def appquietPeriod = app.quietPeriod ?: 0

    println("Creating ${app.name} pipeline jobs")

    def folders = app.basePath.split("/")
    folder(folders[0]) {
        description "JobDSL generated for ${folders[0]}"
    }
    folder(app.basePath) {
        description "JobDSL generated for ${app.basePath}"
        primaryView "Pipelines"
        views {
            categorizedJobsView('Pipelines') {
                jobs {
                    regex(/.*/)
                }
                categorizationCriteria {
                    regexGroupingRule(/^[^_]+/)
                }
                columns {
                    status()
                    categorizedJob()
                    buildButton()
                }
            }
        }
    }

    for (env in app.envs) {
        if (env == 'dev') {
            println("Creating ${env} job: ${app.name}_${env}")
            multibranchPipelineJob("${app.basePath}/${app.name}_${env}") {
                branchSources {
                    branchSource {
                        source {
                            github {
                                id("${app.name}-Github")
                                repoOwner('COMPANY')
                                repository(app.repository)
                                repositoryUrl("https://github.com/COMPANY/${app.repository}")
                                configuredByUrl(true)
                                credentialsId('github-token-unpw')
                                traits {
                                    gitHubBranchDiscovery {
                                        // All branches
                                        strategyId(3)
                                    }
                                    gitHubPullRequestDiscovery {
                                        // Merging the pull request with the current target branch revision
                                        strategyId(1)
                                    }
                                    gitHubIgnoreDraftPullRequestFilter{}
                                }
                            }
                        }
                        strategy {
                            defaultBranchPropertyStrategy {
                                props {
                                    // keep only the last 14 builds
                                    buildRetentionBranchProperty { // deprecated
                                        buildDiscarder {
                                            logRotator {
                                                daysToKeepStr("-1")
                                                numToKeepStr("14")
                                                artifactDaysToKeepStr("-1")
                                                artifactNumToKeepStr("-1")
                                            }
                                        }
                                    }
                                }
                            }
                            namedExceptionsBranchPropertyStrategy {
                                defaultProperties {
                                    noTriggerBranchProperty()
                                }
                                namedExceptions {
                                    named {
                                        name(defaultBranch)
                                    }
                                }
                            }
                        }
                    }
                }
                factory {
                    workflowBranchProjectFactory {
                        scriptPath(appScriptPath)
                    }
                }
                // don't keep build jobs for deleted branches
                orphanedItemStrategy {
                    discardOldItems {
                        numToKeep(-1)
                    }
                }
                configure {
                    it / 'triggers' << 'com.igalg.jenkins.plugins.mswt.trigger.ComputedFolderWebHookTrigger' {
                        spec ''
                        token appToken
                    }
                }
            }
        } else if (env == 'qa') {
            println("Creating ${env} job: ${app.name}_${env}")
            multibranchPipelineJob("${app.basePath}/${app.name}_${env}") {
                branchSources {
                    branchSource {
                        source {
                            github {
                                id("${app.name}-Github")
                                repoOwner('COMPANY')
                                repository(app.repository)
                                repositoryUrl("https://github.com/COMPANY/${app.repository}")
                                configuredByUrl(true)
                                credentialsId('github-token-unpw')
                                traits {
                                    gitHubBranchDiscovery {
                                        // All branches
                                        strategyId(3)
                                    }
                                    gitHubPullRequestDiscovery {
                                        // Merging the pull request with the current target branch revision
                                        strategyId(1)
                                    }
                                    gitHubIgnoreDraftPullRequestFilter{}
                                }
                            }
                        }
                        strategy {
                            defaultBranchPropertyStrategy {
                                props {
                                    // keep only the last 14 builds
                                    buildRetentionBranchProperty { // deprecated
                                        buildDiscarder {
                                            logRotator {
                                                daysToKeepStr("-1")
                                                numToKeepStr("14")
                                                artifactDaysToKeepStr("-1")
                                                artifactNumToKeepStr("-1")
                                            }
                                        }
                                    }
                                }
                            }
                            namedExceptionsBranchPropertyStrategy {
                                defaultProperties {
                                    noTriggerBranchProperty()
                                }
                            }
                        }
                    }
                }
                factory {
                    workflowBranchProjectFactory {
                        scriptPath(appScriptPath)
                    }
                }
                // don't keep build jobs for deleted branches
                orphanedItemStrategy {
                    discardOldItems {
                        numToKeep(-1)
                    }
                }
                configure {
                    it / 'triggers' << 'com.igalg.jenkins.plugins.mswt.trigger.ComputedFolderWebHookTrigger' {
                        spec ''
                        token appToken
                    }
                }
            }
        } else {
            println("Creating ${env} Job: ${app.name}_${env}")
            pipelineJob("${app.basePath}/${app.name}_${env}") {
                properties {
                    office365ConnectorWebhooks {
                        webhooks {
                            webhook {
                                name('Generic Teams Notifier')
                                url('https://TEAMS_HOOK_URL')
                                startNotification(false)
                                notifySuccess(true)
                                notifyAborted(false)
                                notifyNotBuilt(false)
                                notifyUnstable(true)
                                notifyFailure(true)
                                notifyBackToNormal(true)
                                notifyRepeatedFailure(false)
                                timeout(30000)
                            }
                        }
                    }
                }
                parameters(jobParametersClosure)
                definition {
                    logRotator {
                        // keep only the last 14 builds
                        numToKeep(14)
                        daysToKeep(-1)
                        artifactDaysToKeep(-1)
                        artifactNumToKeep(-1)
                    }
                    cpsScm {
                        scriptPath(appScriptPath)
                        lightweight()
                        scm {
                            git {
                                remote {
                                    github("COMPANY/${app.repository}", 'ssh')
                                    credentials('github-pem')
                                }
                                branch(defaultBranch)
                                extensions {
                                    localBranch()
                                }
                            }
                        }
                    }
                    triggers { // deprecated
                        quietPeriod(appquietPeriod)
                        cron(appCronTrigger)
                    }
                }
            }
        }
    }
}

