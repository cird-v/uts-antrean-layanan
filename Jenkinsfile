// Declarative Pipeline - Student Service Queue System (Studi Kasus 3)
// Trigger : GitHub Webhook (push ke branch main) -> https://<ngrok-url>/github-webhook/
// Stage   : Checkout -> Syntax Check -> Build Image -> Automated Deployment -> Health Check

pipeline {
    agent any

    triggers {
        githubPush()
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        COMPOSE_PROJECT_NAME = 'queue-system'
        IMAGE_TAG            = "${env.BUILD_NUMBER}"
        BACKEND_CONTAINER    = 'queue-backend'
        FRONTEND_CONTAINER   = 'queue-frontend'
    }

    stages {
        stage('Checkout') {
            steps {
                // Memakai repo + credential PAT (github-pat) yang diatur di konfigurasi job
                checkout scm
                sh 'git log -1 --pretty=format:"Commit %h oleh %an: %s"'
            }
        }

        stage('Syntax Check') {
            steps {
                sh 'python3 -m py_compile backend/app.py'
                sh 'python3 -m unittest discover -s backend/tests -v'
                sh 'docker compose config --quiet'
                sh 'test -s frontend/index.html && grep -q "fetch(" frontend/index.html'
            }
        }

        stage('Build Image') {
            steps {
                sh 'docker compose build backend'
                sh 'docker tag queue-backend:${IMAGE_TAG} queue-backend:latest'
                sh 'docker image ls queue-backend'
            }
        }

        stage('Automated Deployment') {
            steps {
                // Stop & hapus kontainer lama (TANPA -v, Named Volume queue-db-data tetap aman)
                sh 'docker compose down --remove-orphans'
                sh 'docker compose up -d'
                sh 'docker compose ps'
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    echo "Menunggu backend sehat..."
                    for i in $(seq 1 20); do
                        STATUS=$(docker inspect -f '{{.State.Health.Status}}' "$BACKEND_CONTAINER" 2>/dev/null || echo "missing")
                        echo "  percobaan $i: $STATUS"
                        [ "$STATUS" = "healthy" ] && break
                        sleep 3
                    done
                    [ "$STATUS" = "healthy" ] || { echo "Backend tidak sehat"; exit 1; }

                    echo "1) Backend /health"
                    docker exec "$BACKEND_CONTAINER" python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

                    echo "2) Frontend -> Backend via Service Name (DNS app-net)"
                    for i in $(seq 1 10); do
                        docker exec "$FRONTEND_CONTAINER" wget -qO- http://127.0.0.1/api/queue > /tmp/queue.json 2>/dev/null && break
                        echo "  nginx belum siap, percobaan $i"
                        sleep 2
                    done
                    grep -q '"status": "success"' /tmp/queue.json

                    echo "3) Frontend index.html tersaji dari Bind Mount"
                    docker exec "$FRONTEND_CONTAINER" wget -qO- http://127.0.0.1/ | grep -q "Antrean Layanan Mahasiswa"

                    echo "Semua health check LULUS"
                '''
            }
        }
    }

    post {
        success {
            echo "Deploy build #${env.BUILD_NUMBER} SUKSES -> Frontend http://localhost:3000 | API http://localhost:8000/queue"
        }
        failure {
            sh 'docker compose ps || true'
            sh 'docker compose logs --tail=50 || true'
        }
    }
}
