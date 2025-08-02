#!/bin/groovy

def hideCmd(String command) {
    sh(script: "#!/bin/sh -e\n${command}", returnStdout: true)
}