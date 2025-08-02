#!/bin/groovy
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject


def call(config, jiraPwd) {
    println("Given config: ${config}")

    gitRepo.safeDir()

    config.emailTo = config.emailTo ?: '<EMAIL_ADDRESS>'
    config.jiraURL = config.jiraURL ?: 'https://jira.EXAMPLE.com'
    config.dockerURL = config.dockerURL ?: '<ACCT_ID>.dkr.ecr.us-east-1.amazonaws.com'
    config.dockerFile = config.dockerFile ?: 'Dockerfile'
    config.repoName = gitRepo.repoName()
    config.appName = config.appName ?: config.repoName
    config.branchName = gitRepo.branchName()
    config.commitSha = gitRepo.commitSha()

    if (currentBuild.rawBuild.project.parent instanceof WorkflowMultiBranchProject) {
        def project = currentBuild.rawBuild.project
        def jobName = project.parent.displayName
        config.envName = jobName.tokenize('_')[1]
    } else {
        config.envName = env.JOB_BASE_NAME.tokenize('_')[1]
    }

    println("Environment: ${config.envName}")

    config.appType = config.appType ?: getAppType()
    config.appSubType = config.appSubType ?: 'service'
    config.envDefaults = envDefaults(config.envName)
    config.helmTimeout = config.helmTimeout ?: '300s'
    config.dockerAppName = config.dockerAppName ?: config.appName
    config.purgeCache = config.purgeCache ?: ''

    // Spring Cloud Dataflow
    if (config.appSubType == 'integration') {
        config.dataflow = config.dataflow ?: [:]
        config.dataflow.credId = "okta-dataflow-${config.envName}"
        config.dataflow.type = config.dataflow.type ?: "processor"
        config.dataflow.url = config.dataflow.url ?: "https://scdf-${config.envName}.EXAMPLE.com"
        config.dataflow.setDefaultVersion = config.dataflow.setDefaultVersion ?: true
        config.dataflow.deployStream = config.dataflow.deployStream ?: false
        config.dataflow.definitions = config.dataflow.definitions ?: "${WORKSPACE}/definitions.json"
    }

    // technology specific versions only used for setVersion()
    config.javaVersion = config.javaVersion ?: '17'
    config.pythonVersion = config.pythonVersion ?: '3.8'
    config.nodeVersion = config.nodeVersion ?: '18'

    if (config.appSubType == 'library') {
        config.deploy = false
    }

    config.versionOverride = false
    if (params.version) {
        config.version = params.version
        config.versionOverride = true
        println("Version override was used, not required to discover next version")
    } else {
        config.version = getVersion(config)
    }

    if (config.envName in ['dev','qa','preprod']) {
        if (config.version == getVersion.readVersion(config.appType)) {
            println("Version file already set to ${config.version}.  Not required to update it.")
        } else if (config.skipSetVersion) {
            println("Skipping setVersion() call because you told me to.")
        } else {
            setVersion(config)
        }
    }
    println("Current version is: ${config.version}")

    config.dockerTag = config.version
    if (config.envName in ['dev','qa']) {
         // Set tagPrefix for ECR lifecycle policy
        config.dockerTag = "${config.envName}-${config.version}"
        if (config.version.contains('-SNAPSHOT')) {
            config.dockerTag = "${config.dockerTag}-${config.commitSha}"
        }
    }

    if (config.jiraProject instanceof String) {
        config.jiraProject = config.jiraProject.split() as List
    }

    config.jiraTicketNum = jiraTicket.search(config, jiraPwd)
    config.jiraReleaseId = [:]
    for (project in config.jiraProject) {
        releaseId = jiraRelease.search(config, project, jiraPwd)
        if (!releaseId) {
            continue
        }
        println("Found release for ${project}: ${releaseId}")
        config.jiraReleaseId[project] = releaseId
    }
    println(config.jiraReleaseId)

    if (config.envName == 'preprod') {
        createVersion(config, jiraPwd)
    }

    // Figure out if we build and/or deploy if not specified already
    if (config.build == null) { config.build = doBuild(config) }
    if (config.deploy == null) { config.deploy = doDeploy(config) }

    config.runPurgeCache = false

    // Anything specific to production
    if (config.envName == 'production') {
        if (config.purgeCache) {
            println("Will purge cloudflare cache after deployment")
            config.runPurgeCache = true
        }
    }

    println("Final config: ${config}")

    return config
}