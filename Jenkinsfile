pipeline {
    agent any

    environment {
        // Configure Capsule backend parameters (Production Render URL)
        CAPSULE_API_URL = 'https://capsule-backend-d1fp.onrender.com'
        
        // Fetch API credentials from Jenkins Credential Store
        CAPSULE_API_KEY = credentials('capsule-api-key')
    }

    stages {
        stage('Validate Environment') {
            when {
                expression { return env.CHANGE_ID != null }
            }
            steps {
                script {
                    echo "Processing PR #${env.CHANGE_ID}: Target Branch=${env.CHANGE_TARGET}"
                }
            }
        }

        stage('Analyze Pull Request') {
            when {
                expression { return env.CHANGE_ID != null && env.CHANGE_TARGET != 'main' && env.CHANGE_TARGET != 'master' }
            }
            steps {
                echo "Triggering Capsule AI analysis for PR #${env.CHANGE_ID}..."
                script {
                    def targetRepo = env.GIT_URL ? env.GIT_URL.replaceAll('.*github.com[:/]', '').replaceAll('\\.git$', '') : 'PTejasKr/CApsule-v2'
                    def response = httpRequest(
                        url: "${env.CAPSULE_API_URL}/api/webhooks/jenkins",
                        httpMode: 'POST',
                        contentType: 'APPLICATION_JSON',
                        requestBody: """{
                            \"pr_number\": ${env.CHANGE_ID},
                            \"action\": \"${env.CHANGE_TARGET}\",
                            \"repo\": \"${targetRepo}\"
                        }""",
                        customHeaders: [
                            [name: 'X-API-Key', value: env.CAPSULE_API_KEY]
                        ]
                    )
                    echo "Capsule Analysis Response: ${response.status} - ${response.content}"
                }
            }
        }

        stage('Publish Release Changelog') {
            when {
                expression { return env.CHANGE_ID != null && env.CHANGE_TARGET == 'main' && currentBuild.result == 'SUCCESS' }
            }
            steps {
                echo "PR #${env.CHANGE_ID} merged to main. Generating and publishing changelog..."
                script {
                    def response = httpRequest(
                        url: "${env.CAPSULE_API_URL}/api/pr/${env.CHANGE_ID}/generate-changelog",
                        httpMode: 'POST',
                        customHeaders: [
                            [name: 'X-API-Key', value: env.CAPSULE_API_KEY]
                        ]
                    )
                    echo "Changelog Release Response: ${response.status} - ${response.content}"
                }
            }
        }
    }

    post {
        success {
            echo "Capsule Jenkins integration pipeline completed successfully."
        }
        failure {
            echo "Capsule Jenkins integration pipeline failed. Check logs and backend API connectivity."
        }
    }
}
