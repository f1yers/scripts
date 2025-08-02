#!/bin/groovy

def call(envName) {
"""
Store any settings here that are different only between environment
"""
    def envDefaults = [:]
    envDefaults.build = true
    envDefaults.deploy = true

    // DEV Environment Defaults
    if (envName == 'dev') {
        envDefaults.kubeContext = "EKS-1"
        envDefaults.oktaOrgUrl  = "https://sso.example.com"
    }

    // QA Environment Defaults
    if (envName == 'qa') {
        envDefaults.kubeContext = "EKS-2"
        envDefaults.oktaOrgUrl  = "https://sso.example.com"
    }

    // UAT Environment Defaults
    if (envName == 'preprod' || envName == 'uat' || envName == 'release') {
        envDefaults.transistionId = "21"
        envDefaults.kubeContext = "EKS-2"
        envDefaults.oktaOrgUrl  = "https://sso.example.com"
    }

    // Production Environment Defaults
    if (envName == 'production' || envName == 'prd') {
        envDefaults.kubeContext = 'EKS-3'
        envDefaults.build = false
        envDefaults.transistionId = "61"
        envDefaults.oktaOrgUrl  = "https://sso.example.com"
    }

    // Demo Environment Defaults
    if (envName == 'demo') {
        envDefaults.kubeContext = "EKS-4"
        envDefaults.build = false
        envDefaults.transistionId = "41"
        envDefaults.oktaOrgUrl  = "https://sso.example.com"
    }

    return envDefaults
}