#!/bin/groovy

def call(config, jiraPwd) {

    if (!config.jiraTicketNum) {
        config.jiraTicketNum = jiraTicket.create(config, jiraPwd)
    }
    println("Ticket for this release is ${config.jiraTicketNum}")


    for (project in config.jiraProject) {
        if (!config.jiraReleaseId.containsKey(project)) {
            println("Could not find a release ID for ${config.version} in ${project}.  Attempting to create one now...")
            config.jiraReleaseId[project] = jiraRelease.create(config, project, jiraPwd)
        }
        println("Release ID for ${config.version} in ${project} is ${config.jiraReleaseId[project]}")
    }
    return config
}