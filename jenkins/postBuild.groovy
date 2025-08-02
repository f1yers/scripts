#!/bin/groovy

def call(config, jiraPwd) {

    if (config.envName == 'preprod') {
        for (project in config.jiraProject) {
            jiraTicketLink(config, project, config.jiraReleaseId[project], jiraPwd)
            jiraRelease.released(config, config.jiraReleaseId[project], jiraPwd)
        }
        gitRepo.tag(config)
    }

    if (config.envName != 'dev') {
        jiraTicket.comment(config, jiraPwd)
        jiraTicket.transistion(config, jiraPwd)
        emailext (
            mimeType: 'text/html',
            to: config.emailTo,
            subject: "${config.appName} - ${config.version} - ${config.envName.toUpperCase()} Deployment",
            body: """<p>${config.appName}:${config.version} was deployed to ${config.envName.toUpperCase()}.</p>
            <p>Console output can be viewed <a href='${env.BUILD_URL}'>here</a></p>"""
        )
    }
}