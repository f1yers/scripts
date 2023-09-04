#!/bin/groovy

pipeline {
    agent any
    stages {
        stage('Mover') {
            steps {
                script {
                    deleteDir()
                    def qbittorent_host = "192.168.1.151:8080"
                    def src_tv = "/downloads/completed/tv"
                    def src_4k = "/downloads/completed/4K"
                    def src_movies = "/downloads/completed/movies"

                    def src_locations = [src_tv, src_4k, src_movies]

                    torrent_auth()
                    seed_map = seeding()
                    seed_list = []
                    for (s in seed_map) {
                        seed_list.add(s.name)
                    }
                    in_progress = []
                    println("Beginning mover loop...")
                    for (location in src_locations) {
                        completed = []
                        def files = sh(script: "ls ${location}", returnStdout: true).trim()
                        def all_files = each_line(files, location)
                        for (file in all_files) {
                            if (!seed_list.contains(file)) {
                                completed.add(file)
                            } else {
                                in_progress.add(file)
                            }
                        }
                        dest_location = '/plexdata/' + location.minus('/downloads/completed/')
                        println("Will move the following files to ${dest_location}\r${completed}")
                        for (c in completed) {
                            mover(c, location, dest_location)
                        }
                    }
                    println("Mover loop completed.  The following files were skipped because they are seeding:\r${in_progress}")
                }
            }
        }
    }
}

def torrent_auth() {
    withCredentials([string(credentialsId: 'qbittorrent_admin_password', variable: 'qbittorrent_admin_password')]) {
        sh(script: "curl -isS -c $WORKSPACE/cookie.txt -H \"Referer: http://${qbittorent_host}\" -d \"username=nathan&password=${qbittorrent_admin_password}\" http://${qbittorent_host}/api/v2/auth/login", returnStdout: true)
    }
}

@NonCPS
def each_line(files, location) {
    all_files = []
    files.eachLine {
        all_files.add(it)
    }
    return all_files
}

def seeding() {
    r = sh(script: "curl -Ss -b $WORKSPACE/cookie.txt -H 'Accept: application/json' -H 'Content-Type: application/json' http://${qbittorent_host}/api/v2/torrents/info?filter=seeding > $WORKSPACE/seeding.json")
    seed_map = readJSON file: "$WORKSPACE/seeding.json"
    return seed_map
}

def mover(file, src_location, dest_location) {
    try {
        sh(script: """mv -fvn \"${src_location}/${file}\" ${dest_location}/""", returnStdout: true)
    } catch(Exception e) {
        println("Failed to move \"${src_location}/${file}\" due to: ${e}")
    }
}
