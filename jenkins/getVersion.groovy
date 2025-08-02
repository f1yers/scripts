#!/bin/groovy
import com.mbopartners.*

def call(config) {

    // read what version is currently set
    config.version = readVersion(config.appType)
    println("Current version is set to ${config.version}")

    // versioning logic for DEV builds
    if (config.envName in ['dev','qa']) {
        // if version has -SNAPSHOT, just read it in
        if (config.version.contains("-SNAPSHOT")) {
            println("No version update will take place. Using SNAPSHOT version already set in pom.xml")
        } else if (config.appType == 'python' || config.appType == 'nodejs') {
            // always set node & python dev/qa builds to currentVersion-commitSha
            config.currentVersion = readVersion(config.appType)
            config.version = "${config.currentVersion}-${config.commitSha}"
        } else {
            config.version = config.commitSha
        }
    }

    // versioning logic for PREPROD builds
    if (config.envName == 'preprod') {
        if (config.version?.contains('-')) {
            config.version = config.version.split('-')[0] // Drop any non-semver appended identifier
        } else {
            def semVersion = new SemVer(config.version)
            config.version = semVersion.bump(PatchLevel.PATCH).toString()
        }
    }

    return config.version
}

def readVersion(appType) {

    if (appType == 'java') {
        pom = readMavenPom file: 'pom.xml'
        version = pom.version
    } else if (appType == 'python') {
        version = sh(script: "python3 setup.py --version", returnStdout: true).trim()
    } else if (appType == 'nodejs') {
        Map packageJson = readJSON(file: "package.json")
        version = packageJson.version
    } else {
        version = gitRepo.getLatestTag().replaceFirst("^v","")
    }

    return version
}