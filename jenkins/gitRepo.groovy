#!/bin/groovy

def safeDir() {
    // https://github.com/git/git/commit/8959555cee7ec045958f9b6dd62e541affb7e7d9
    sh "git config --global --add safe.directory ${WORKSPACE}"
}
def repoName() {
    return sh(script: "git config --get remote.origin.url", returnStdout: true).trim().replaceFirst(/^.*\/([^\/]+?).git$/, '$1')
}

def branchName() {
    return sh(script: "git rev-parse --abbrev-ref HEAD", returnStdout: true).trim()
}

def commitSha() {
    return sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
}

def tag(config) {
    sh "git tag -a v${config.version} -m \"REL Ticket: ${config.jiraTicketNum}\" || echo \"tag v${config.version} already exists\""
    sh "git push origin v${config.version}"
}

def getLatestTag() {
    return sh(script: "git describe --abbrev=0 2> /dev/null || echo \"v0.0.0\"", returnStdout: true).trim()
}

def pushVersion(config) {
    sh "git pull origin ${config.branchName}"
    switch(config.appType) {
        case 'java':
            sh "git add pom.xml"
            sh "git add **/pom.xml || echo \"no other poms found\""
            break
        case 'python':
            sh "git add setup.py"
            break
        case 'nodejs':
            sh "git add package.json"
            break
    }
    sh "git diff-index --quiet HEAD || git commit -m \"updated version to ${config.version}\""
    sh "git push origin ${config.branchName}"
}

def checkOutDevOps(config) {
    dir ('dev-ops') {
        git url: 'git@github.com:mbopartnersinc/dev-ops.git',
            branch: config.devOpsBranch ?: "master",
            credentialsId: 'github-pem'
    }
}

def configure() {
    sh 'mkdir /home/jenkins/.ssh && mv /home/jenkins/agent/known_hosts /home/jenkins/.ssh/known_hosts' // Inject mounted known_hosts into jnpl ~/.ssh
    sh 'git config --global user.email \"noreply@EXAMPLE.com\"'
    sh 'git config --global user.name \"Release Automation\"'
}