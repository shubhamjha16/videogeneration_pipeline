pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-south-1'
        PROJECT_NAME = 'easetolearn-factory'
        AWS_CREDENTIALS_ID = 'aws-credentials-id' // Ensure this matches your Jenkins credentials ID
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                echo '🚀 Running Automated Tests...'
                sh '''
                    if [ ! -d "tests" ]; then
                        echo "❌ ERROR: 'tests/' directory not found. Check gitignore settings."
                        exit 1
                    fi
                    python3 -m pip install -r requirements.txt
                    python3 -m pytest tests/ --maxfail=1 --disable-warnings
                '''
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([[
                    $class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: "${env.AWS_CREDENTIALS_ID}",
                    accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                ]]) {
                    echo '🏗️ Deploying to AWS ECS via Infrastructure Script...'
                    sh 'bash infrastructure/deploy.sh'
                }
            }
        }
    }

    post {
        success {
            echo '✅ Deployment Successful!'
        }
        failure {
            echo '❌ Deployment Failed. Check console logs for details.'
        }
    }
}
