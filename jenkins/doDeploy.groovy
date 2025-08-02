#!/bin/groovy

def call(config) {
"""
Returns true if pipeline should deploy to K8s
"""
    println("Called doDeploy, returning environment default")
    return config.envDefaults.deploy
}