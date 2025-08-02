#!/bin/groovy


def call(Map config = [:], Map closures = [:]) {

    // Default (overridable) Configurations

    // default node: c5.2xlarge (current instance max: 8cpu ~16gb memory/minus system and other containers)
    config.nodeSelector   = config.get('nodeSelector', 'jenkins-agent-large-nodes')
    // https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

    // Limits
    config.podMemoryLimit = config.get('podMemoryLimit', '8192M')
    config.podCpuLimit    = config.get('podCpuLimit', '8000m')

    // Requests (If set too high container may be unschedulable)
    config.podMemoryReq   = config.get('podMemoryReq', '4096M')
    config.podCpuReq      = config.get('podCpuReq', '4000m')

    config.containerName  = config.get('containerName', 'maven:3.8-openjdk-11-chrome-134-awscli')
    config.teamsWebhook   = config.get('teamsWebhook', '')
    config.emailTo        = config.get('emailTo', '')
    config.testCmd        = config.get('testCmd', "mvn clean test -s /usr/share/maven/conf/settings.xml -Dtags=\"$config.CUCUMBER_TAGS\"")

    println("Invoking build with the following properties:\n \
             Config: ${config}")

    // Support for closure defaults
    Closure defaultSetup = { ->
        echo "Executing default setup"
    }

    Closure defaultArchiveAndPublish = { ->
        echo "Executing default archive and publish"

        archiveArtifacts allowEmptyArchive: true, artifacts: 'target/dump.json'
        archiveArtifacts allowEmptyArchive: true, artifacts: 'target/mboats.html'
        archiveArtifacts allowEmptyArchive: true, artifacts: 'target/props.properties'
        publishHTML([allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true, reportDir: 'target', reportFiles: 'mboats.html', reportName: "${config.projectName} Report", reportTitles: "MBOATS ${config.projectName} Report"])
        script {
            def props = readProperties file: 'target/props.properties'
            env.passed = props.passed
            env.failed = props.failed
            env.skipped = props.skipped
            env.total = props.total
            env.report_url = props.report_url
            env.environment = props.environment
        }
        echo "Total : $total"
        emailext attachmentsPattern: 'cicd/mbo-logo.png,target/mboats.html', body: """<html>
                <body>
                </body>
            </html>""",
            mimeType: 'text/html',
            subject: '${DEFAULT_SUBJECT}',
            replyTo: 'someone@example.com',
            from: 'noreply@example.com',
            to: "${config.emailTo}"

        office365ConnectorSend webhookUrl: config.teamsWebhook,
            factDefinitions: [
                [name: 'Environment', template: "${environment}"],
                [name: 'Passed', template: "${passed}"],
                [name: 'Failed', template: "${failed}"],
                [name: 'Skipped', template: "${skipped}"],
                [name: 'Total', template: "${total}"]
            ],
            message: "Test Automation Execution Results: [Report](${BUILD_URL}artifact/target/mboats.html)",
            status: 'Build Success',
            color: '00ff00'
    }

    // Supported closures
    Closure setup = closures.get("setup", defaultSetup)
    Closure archiveAndPublish = closures.get("archiveAndPublish", defaultArchiveAndPublish)

    podTemplate(yaml: """
apiVersion: v1
kind: Pod
spec:
  tolerations:
  - key: "$config.nodeSelector"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
  nodeSelector:
    $config.nodeSelector: "true"
  initContainers:
  - name: copy-known-hosts
    image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/busybox:latest
    command: ['sh', '-c', 'cp /root/.ssh/known_hosts /home/jenkins/agent/known_hosts && chmod 644 /home/jenkins/agent/known_hosts']
    volumeMounts:
    - name: ssh-config
      mountPath: /root/.ssh
    - name: workspace-volume
      mountPath: /home/jenkins/agent
  containers:
  - name: default
    image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/$config.containerName
    command:
    - cat
    tty: true
    resources:
      requests:
        memory: $config.podMemoryReq
        cpu: $config.podCpuReq
      limits:
        memory: $config.podMemoryLimit
        cpu: $config.podCpuLimit
    env:
    - name: AWS_DEFAULT_REGION
      value: "us-east-1"
    - name: AWS_DEFAULT_OUTPUT
      value: "json"
    envFrom:
    - secretRef:
        name: test-automation-secrets
    volumeMounts:
    - name: maven-settings-xml
      mountPath: /usr/share/maven/conf/settings.xml
      subPath: settings.xml
    - name: npmrc
      mountPath: /root/.npmrc
      subPath: .npmrc
    - name: ssh-config
      mountPath: /root/.ssh
  - name: build-tools
    image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/build-tools:07142023.1
    command:
    - cat
    tty: true
    resources:
      requests:
        memory: "512M"
        cpu: "1000m"
      limits:
        memory: "1024M"
        cpu: "2000m"
    env:
    - name: AWS_DEFAULT_REGION
      value: "us-east-1"
    - name: AWS_DEFAULT_OUTPUT
      value: "json"
    volumeMounts:
    - name: ssh-config
      mountPath: /root/.ssh
  volumes:
  - name: ssh-config
    secret:
      secretName: jenkins-configs
      defaultMode: 256
  - name: "maven-settings-xml"
    configMap:
      name: "maven-settings-xml-codeartifact"
      items:
      - key: settings.xml
        path: settings.xml
  - name: "npmrc"
    configMap:
      name: "npmrc-codeartifact"
      items:
      - key: .npmrc
        path: .npmrc""") {
        node(POD_LABEL) {
            try {
                stage('Setup') {
                    gitRepo.configure()
                    checkout scm

                    script {
                        setup()
                    }
                }
                stage('Test') {
                    container("default") {
                        env.CODEARTIFACT_AUTH_TOKEN = doBuild.caAuth('3600')
                        sh config.testCmd
                    }
                }
                stage('Archive and Publish') {
                    script {
                        archiveAndPublish(config)
                    }
                }
            }
            catch(Exception e) {
                office365ConnectorSend webhookUrl: config.teamsWebhook,
                    factDefinitions: [[name: 'Reason', template: "${e}"]],
                    message: 'Test Automation Failure',
                    status: 'Build Failure',
                    color: 'ff0000'
                throw e
            }
        }
    }
}

