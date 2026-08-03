BENCHMARK_TASKS = [
    # ============================================================
    # DOCKER (001-020)
    # ============================================================
    {
        "id": "docker-001",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a multi-stage Dockerfile for a Go application. Stage 1: build the binary using golang:1.21-alpine. Stage 2: copy the binary into a distroless image. Add proper labels (maintainer, version), set the binary as the entrypoint, and listen on port 8080.",
        "expected_patterns": [
            "FROM golang:1.21-alpine AS builder",
            "COPY --from=builder",
            "gcr.io/distroless",
            "EXPOSE 8080",
            "ENTRYPOINT",
            "LABEL"
        ],
        "description": "Multi-stage Dockerfile for Go app with distroless final stage",
        "language": "dockerfile"
    },
    {
        "id": "docker-002",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a docker-compose.yml for a web application with three services: a Python Flask API (build from ./api), a PostgreSQL database (image: postgres:16, with named volume for persistence), and a Redis cache (image: redis:7-alpine). The API must depend on both db and redis. Use a custom bridge network. Mount a bind volume for the API source code on the api service for hot-reloading.",
        "expected_patterns": [
            "services:",
            "volumes:",
            "networks:",
            "depends_on:",
            "driver: bridge",
            "postgres:16"
        ],
        "description": "Docker compose with API, PostgreSQL, Redis, named volume, bind mount, and custom bridge network",
        "language": "yaml"
    },
    {
        "id": "docker-003",
        "domain": "docker",
        "difficulty": "easy",
        "prompt": "Add a HEALTHCHECK instruction to a Dockerfile for a Node.js Express app. Use curl to hit the /health endpoint. Set the interval to 30s, timeout to 10s, retries to 3, and start period to 15s.",
        "expected_patterns": [
            "HEALTHCHECK",
            "curl",
            "--interval=30s",
            "--timeout=10s",
            "--retries=3",
            "--start-period=15s"
        ],
        "description": "Dockerfile HEALTHCHECK for Node.js Express app",
        "language": "dockerfile"
    },
    {
        "id": "docker-004",
        "domain": "docker",
        "difficulty": "beginner",
        "prompt": "Write a Dockerfile for a Python script that runs a long-running data processing job. Use CMD to run `python process.py`. Then modify the same Dockerfile to instead use ENTRYPOINT with CMD as default arguments so users can pass different scripts at runtime. Explain when each approach is appropriate.",
        "expected_patterns": [
            "ENTRYPOINT",
            "CMD",
            "python"
        ],
        "description": "Compare ENTRYPOINT vs CMD in a Python Dockerfile",
        "language": "dockerfile"
    },
    {
        "id": "docker-005",
        "domain": "docker",
        "difficulty": "beginner",
        "prompt": "Write a .dockerignore file for a Python project that excludes virtual environments (.venv, env, venv), cache directories (__pycache__, .pytest_cache, .mypy_cache), IDE files (.vscode, .idea), git history (.git), OS files (.DS_Store), and environment files (.env).",
        "expected_patterns": [
            "__pycache__",
            ".venv",
            ".git",
            ".env",
            ".vscode",
            ".DS_Store"
        ],
        "description": "Dockerignore for Python project excluding venvs, caches, IDE files",
        "language": "dockerfile"
    },
    {
        "id": "docker-006",
        "domain": "docker",
        "difficulty": "easy",
        "prompt": "Write docker run commands that demonstrate the difference between bind mounts and named volumes. First, run a container using a bind mount to share the host directory ./data with /app/data inside the container. Second, create a named volume called 'app-data' and mount it to /app/data. Show how to inspect the volume and remove it.",
        "expected_patterns": [
            "docker run",
            "--mount type=bind",
            "docker volume create",
            "--mount type=volume",
            "docker volume inspect",
            "docker volume rm"
        ],
        "description": "Demonstrate bind mount vs named volume with docker run commands",
        "language": "bash"
    },
    {
        "id": "docker-007",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a set of docker commands and a docker-compose overlay configuration that demonstrates three Docker network drivers: bridge, host, and overlay. Create a user-defined bridge network and attach two containers. Show how host mode bypasses network isolation. Write a docker-compose overlay config for a Docker Swarm service. Include the command to initialize a Swarm.",
        "expected_patterns": [
            "docker network create",
            "driver: bridge",
            "network_mode: host",
            "driver: overlay",
            "docker swarm init"
        ],
        "description": "Demonstrate bridge, host, and overlay network drivers",
        "language": "yaml"
    },
    {
        "id": "docker-008",
        "domain": "docker",
        "difficulty": "hard",
        "prompt": "Write a docker-compose.yml that demonstrates Docker secrets management in Swarm mode. Define two secrets: 'db_password' (from file) and 'api_key' (externally managed). Create a service that uses both secrets mounted at /run/secrets/. Include a python script block that reads both secrets from the filesystem. Initialize the swarm and deploy the stack.",
        "expected_patterns": [
            "secrets:",
            "external:",
            "file:",
            "/run/secrets/",
            "docker stack deploy"
        ],
        "description": "Docker secrets with Swarm mode, external and file-based secrets",
        "language": "yaml"
    },
    {
        "id": "docker-009",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a bash script that uses docker buildx to create and use a multi-architecture builder instance, then builds a Docker image for both linux/amd64 and linux/arm64 simultaneously, and pushes the multi-arch manifest to a registry. Tag the image as 'myapp:latest' and 'myapp:1.0.0'.",
        "expected_patterns": [
            "docker buildx create",
            "docker buildx use",
            "docker buildx build",
            "--platform linux/amd64,linux/arm64",
            "--push",
            "--tag"
        ],
        "description": "Docker buildx multi-architecture builder setup and push",
        "language": "bash"
    },
    {
        "id": "docker-010",
        "domain": "docker",
        "difficulty": "beginner",
        "prompt": "Write a Dockerfile for an Nginx web server that serves a static website. Use the official nginx:alpine image. Add LABEL instructions with the project name, maintainer, and version. Set the LABEL namespace to 'com.example.project'. Document how to inspect labels on a built image.",
        "expected_patterns": [
            "FROM nginx:alpine",
            "LABEL com.example.project",
            "LABEL maintainer",
            "LABEL version",
            "docker inspect"
        ],
        "description": "Dockerfile with LABEL instructions for Nginx Alpine",
        "language": "dockerfile"
    },
    {
        "id": "docker-011",
        "domain": "docker",
        "difficulty": "hard",
        "prompt": "Write a buildx command pipeline that builds a Docker image for linux/amd64, linux/arm64, and linux/arm/v7 simultaneously. Use a QEMU-based builder instance for emulation. Export the build cache to a registry for faster subsequent builds. Tag with both 'myapp:latest' and 'myapp:${VERSION}'. Show the full workflow from builder creation to manifest inspection.",
        "expected_patterns": [
            "docker buildx create",
            "--driver docker-container",
            "qemu",
            "--platform",
            "--cache-to",
            "--cache-from",
            "docker buildx imagetools inspect"
        ],
        "description": "Multi-platform build with QEMU and registry cache",
        "language": "bash"
    },
    {
        "id": "docker-012",
        "domain": "docker",
        "difficulty": "beginner",
        "prompt": "Write docker exec commands to: open an interactive bash shell in a running container named 'myapp', run a single command non-interactively (e.g. 'ls -la /app'), check environment variables inside the container, and run a command as a different user (uid 1001). Explain the difference between docker exec and docker attach.",
        "expected_patterns": [
            "docker exec -it",
            "docker exec myapp ls -la",
            "docker exec myapp env",
            "docker exec --user",
            "docker attach"
        ],
        "description": "Docker exec usage: interactive shell, single command, env, user flag",
        "language": "bash"
    },
    {
        "id": "docker-013",
        "domain": "docker",
        "difficulty": "beginner",
        "prompt": "Write docker logs commands to: show all logs from a container, follow logs in real time (tail -f), show only the last 50 lines, show logs with timestamps, show logs since 10 minutes ago, and filter logs by a specific string using grep. Explain the difference between json-file and journald logging drivers.",
        "expected_patterns": [
            "docker logs",
            "--follow",
            "--tail 50",
            "--timestamps",
            "--since",
            "logging driver"
        ],
        "description": "Docker logs: follow, tail, timestamps, since filter, logging drivers",
        "language": "bash"
    },
    {
        "id": "docker-014",
        "domain": "docker",
        "difficulty": "easy",
        "prompt": "Write docker stats commands and a docker-compose resource constraint configuration. Show how to: stream live stats for all running containers, get a one-shot stats snapshot for a specific container, format stats output as JSON. In docker-compose, set memory limit to 512M and CPU limit to 0.5 cores for a service.",
        "expected_patterns": [
            "docker stats",
            "--no-stream",
            "--format",
            "deploy:",
            "resources:",
            "memory: 512M",
            "cpus:"
        ],
        "description": "Docker stats live monitoring and docker-compose resource constraints",
        "language": "bash"
    },
    {
        "id": "docker-015",
        "domain": "docker",
        "difficulty": "easy",
        "prompt": "Write docker run commands and a docker-compose.yml that demonstrate setting memory and CPU constraints. Run a container with --memory=256m --cpus=0.5 --memory-swap=512m. In docker-compose version 3.8, define a service with deploy.resources.limits setting memory to 256M and cpus to '0.25'. Explain what happens when a container exceeds its memory limit.",
        "expected_patterns": [
            "--memory=256m",
            "--cpus=0.5",
            "--memory-swap=512m",
            "deploy:",
            "resources:",
            "limits:",
            "OOM"
        ],
        "description": "Docker memory and CPU resource constraints with run and compose",
        "language": "yaml"
    },
    {
        "id": "docker-016",
        "domain": "docker",
        "difficulty": "easy",
        "prompt": "Write a docker-compose.yml that demonstrates all Docker restart policies. Define four services: 'always-service' (restart: always), 'unless-stopped-service' (restart: unless-stopped), 'on-failure-service' (restart: on-failure with max retries of 5), and 'no-service' (restart: no). Explain the behavior difference between always and unless-stopped on daemon restart.",
        "expected_patterns": [
            "restart: always",
            "restart: unless-stopped",
            "restart: on-failure",
            "restart: no",
            "max_attempts: 5"
        ],
        "description": "Docker restart policies: always, unless-stopped, on-failure, no",
        "language": "yaml"
    },
    {
        "id": "docker-017",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a Dockerfile that demonstrates Docker layer caching best practices for a Python application. Start with a pinned base image, install system dependencies in one layer, copy and install only requirements.txt first (before copying source code) to leverage cache, use a virtual environment, and switch to a non-root user. Add comments explaining why each order choice matters for cache efficiency.",
        "expected_patterns": [
            "FROM python:3.12-slim",
            "COPY requirements.txt",
            "RUN pip install",
            "COPY .",
            "RUN adduser",
            "USER"
        ],
        "description": "Dockerfile layer caching best practices for Python app",
        "language": "dockerfile"
    },
    {
        "id": "docker-018",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a Dockerfile for a Node.js application that runs as a non-root user. Create a user called 'nodeuser' with uid 1001, copy only production dependencies (skip devDependencies), use npm ci for deterministic installs, set NODE_ENV=production, and use a slim base image. Ensure the application runs on port 3000 as the non-root user.",
        "expected_patterns": [
            "FROM node:20-slim",
            "RUN useradd",
            "npm ci",
            "--omit=dev",
            "NODE_ENV=production",
            "USER nodeuser",
            "EXPOSE 3000"
        ],
        "description": "Dockerfile with non-root user for Node.js production app",
        "language": "dockerfile"
    },
    {
        "id": "docker-019",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a multi-stage Dockerfile for a Python application using a virtual environment. Stage 1: use python:3.12-slim, create a venv, install dependencies from requirements.txt. Stage 2: copy the venv from stage 1 and the application code into a clean python:3.12-slim image. Set PATH to include the venv bin directory. Add health check and run as non-root user.",
        "expected_patterns": [
            "FROM python:3.12-slim AS builder",
            "COPY --from=builder",
            "python -m venv",
            "ENV PATH",
            "HEALTHCHECK",
            "USER"
        ],
        "description": "Multi-stage Dockerfile with Python venv for smaller final image",
        "language": "dockerfile"
    },
    {
        "id": "docker-020",
        "domain": "docker",
        "difficulty": "medium",
        "prompt": "Write a docker-compose.yml for a full-stack application with: a React frontend (build from ./frontend, served via nginx), a Django API backend (build from ./backend), PostgreSQL with a named volume, Redis for caching, and an nginx reverse proxy. Use a shared network. Add health checks for all services. Configure the Django service to wait for postgres before starting.",
        "expected_patterns": [
            "services:",
            "healthcheck:",
            "depends_on:",
            "volumes:",
            "networks:",
            "postgres",
            "redis"
        ],
        "description": "Full-stack compose: React + Django + PostgreSQL + Redis + nginx proxy",
        "language": "yaml"
    },
    # ============================================================
    # KUBERNETES (001-015)
    # ============================================================
    {
        "id": "k8s-001",
        "domain": "kubernetes",
        "difficulty": "medium",
        "prompt": "Write a Kubernetes Pod manifest for a web application container named 'web-app' using image 'nginx:1.25'. Add a liveness probe that checks HTTP GET /health on port 80 with initial delay 5s, period 10s. Add a readiness probe that checks TCP socket on port 80 with initial delay 3s, period 5s. Set resource requests to 128Mi memory and 250m CPU; limits to 256Mi memory and 500m CPU.",
        "expected_patterns": [
            "kind: Pod",
            "livenessProbe:",
            "readinessProbe:",
            "httpGet:",
            "tcpSocket:",
            "resources:",
            "requests:",
            "limits:"
        ],
        "description": "Pod with liveness/readiness probes and resource limits",
        "language": "yaml"
    },
    {
        "id": "k8s-002",
        "domain": "kubernetes",
        "difficulty": "medium",
        "prompt": "Write a Kubernetes Deployment manifest for an app called 'myapp' with 3 replicas using image 'myapp:1.0.0'. Configure a rolling update strategy with maxSurge=1 and maxUnavailable=0. Add a revisionHistoryLimit of 5. Include labels (app: myapp, tier: frontend). Add a startup probe for slow-starting containers. Use container port 3000.",
        "expected_patterns": [
            "kind: Deployment",
            "replicas: 3",
            "strategy:",
            "rollingUpdate:",
            "maxSurge: 1",
            "maxUnavailable: 0",
            "revisionHistoryLimit: 5",
            "startupProbe:"
        ],
        "description": "Deployment with rolling update strategy and startup probe",
        "language": "yaml"
    },
    {
        "id": "k8s-003",
        "domain": "kubernetes",
        "difficulty": "easy",
        "prompt": "Write Kubernetes Service manifests that expose the same deployment (app: myapp, port 8080) using ClusterIP (default, for internal access) and NodePort (for external access on port 30080). Include proper selectors and port naming.",
        "expected_patterns": [
            "kind: Service",
            "type: ClusterIP",
            "type: NodePort",
            "nodePort: 30080",
            "selector:",
            "ports:"
        ],
        "description": "ClusterIP and NodePort Services for same deployment",
        "language": "yaml"
    },
    {
        "id": "k8s-004",
        "domain": "kubernetes",
        "difficulty": "easy",
        "prompt": "Write a ConfigMap with database configuration values (host: postgres-svc, port: 5432, dbname: myapp) and a Secret with base64-encoded username and password (admin / s3cr3t). Then write a Pod that consumes the ConfigMap as environment variables and the Secret as both environment variables and a volume mount at /etc/secrets.",
        "expected_patterns": [
            "kind: ConfigMap",
            "kind: Secret",
            "type: Opaque",
            "data:",
            "envFrom:",
            "volumes:",
            "secret:"
        ],
        "description": "ConfigMap and Secret consumed as env vars and volume mount",
        "language": "yaml"
    },
    {
        "id": "k8s-005",
        "domain": "kubernetes",
        "difficulty": "hard",
        "prompt": "Write an Ingress manifest for a Kubernetes cluster using the nginx ingress controller. Route traffic for api.example.com to a service named 'api-service' on port 8080 and app.example.com to a service named 'web-service' on port 80. Enable TLS with a secret named 'example-tls'. Add annotations for ingress class 'nginx' and SSL redirect.",
        "expected_patterns": [
            "kind: Ingress",
            "nginx.ingress.kubernetes.io",
            "tls:",
            "hosts:",
            "secretName:",
            "rules:",
            "host:"
        ],
        "description": "Ingress with TLS, host-based routing, and nginx annotations",
        "language": "yaml"
    },
    {
        "id": "k8s-006",
        "domain": "kubernetes",
        "difficulty": "medium",
        "prompt": "Write a PersistentVolume named 'data-pv' with 10Gi capacity, accessMode ReadWriteOnce, hostPath /mnt/data, and reclaimPolicy Retain. Then write a PersistentVolumeClaim named 'data-pvc' requesting 5Gi with accessMode ReadWriteOnce. Finally, write a Pod that mounts the PVC at /app/data. Show how to verify the binding status.",
        "expected_patterns": [
            "kind: PersistentVolume",
            "kind: PersistentVolumeClaim",
            "capacity:",
            "accessModes:",
            "persistentVolumeReclaimPolicy: Retain",
            "hostPath:",
            "claimName:"
        ],
        "description": "PersistentVolume, PVC, and Pod consuming the volume",
        "language": "yaml"
    },
    {
        "id": "k8s-007",
        "domain": "kubernetes",
        "difficulty": "hard",
        "prompt": "Write a StatefulSet manifest for a Cassandra cluster with 3 replicas. Use a headless service named 'cassandra' for DNS-based pod discovery. Each pod should have a stable network identity (cassandra-0, cassandra-1, cassandra-2). Mount a PersistentVolumeClaim template named 'data' with 50Gi. Configure rolling update with partition: 1 for canary deployments.",
        "expected_patterns": [
            "kind: StatefulSet",
            "serviceName:",
            "volumeClaimTemplates:",
            "replicas: 3",
            "updateStrategy:",
            "rollingUpdate:",
            "partition: 1"
        ],
        "description": "StatefulSet for Cassandra with headless service and PVC templates",
        "language": "yaml"
    },
    {
        "id": "k8s-008",
        "domain": "kubernetes",
        "difficulty": "medium",
        "prompt": "Write a DaemonSet manifest that deploys a log collector (image: fluentd:latest) on every node in the cluster. Mount the host's /var/log directory to /var/log in the container and /var/lib/docker/containers to /var/lib/docker/containers. Use tolerations to ensure it runs on control-plane nodes as well. Set a priority class name of 'system-cluster-critical'.",
        "expected_patterns": [
            "kind: DaemonSet",
            "tolerations:",
            "effect: NoSchedule",
            "hostPath:",
            "priorityClassName: system-cluster-critical"
        ],
        "description": "DaemonSet for fluentd log collector running on all nodes",
        "language": "yaml"
    },
    {
        "id": "k8s-009",
        "domain": "kubernetes",
        "difficulty": "medium",
        "prompt": "Write a Job manifest that runs a batch computation (image: python:3.12-slim) that executes a python script to process data. Set backoffLimit to 3, completions to 1, parallelism to 1, and activeDeadlineSeconds to 600. Then write a CronJob manifest that runs a database backup script every day at 2:30 AM UTC. Set concurrencyPolicy to Forbid, successfulJobsHistoryLimit to 3, and failedJobsHistoryLimit to 1.",
        "expected_patterns": [
            "kind: Job",
            "backoffLimit: 3",
            "activeDeadlineSeconds: 600",
            "kind: CronJob",
            "schedule:",
            "concurrencyPolicy: Forbid",
            "successfulJobsHistoryLimit: 3",
            "failedJobsHistoryLimit: 1"
        ],
        "description": "Job with backoff limits and CronJob for scheduled backups",
        "language": "yaml"
    },
    {
        "id": "k8s-010",
        "domain": "kubernetes",
        "difficulty": "hard",
        "prompt": "Write a HorizontalPodAutoscaler manifest that scales a deployment named 'api-server' between 2 and 10 replicas. Configure target CPU utilization of 60% and memory utilization of 70%. Use the autoscaling/v2 API version with metrics including both resource metrics and a custom metric from Prometheus (requests-per-second). Set a stabilization window of 60 seconds for scale-down.",
        "expected_patterns": [
            "apiVersion: autoscaling/v2",
            "kind: HorizontalPodAutoscaler",
            "minReplicas: 2",
            "maxReplicas: 10",
            "targetAverageUtilization: 60",
            "stabilizationWindowSeconds: 60",
            "type: Pods"
        ],
        "description": "HPA with CPU, memory, and custom Prometheus metric with scale-down stabilization",
        "language": "yaml"
    },
    {
        "id": "k8s-011",
        "domain": "kubernetes",
        "difficulty": "expert",
        "prompt": "Write a Kubernetes NetworkPolicy manifest for a three-tier application. Create a deny-all ingress policy for the 'default' namespace. Then create a policy that allows: (1) ingress traffic to 'frontend' pods from anywhere on port 80, (2) ingress traffic to 'api' pods only from 'frontend' pods on port 8080, (3) ingress traffic to 'db' pods only from 'api' pods on port 5432. Use podSelector and namespaceSelector appropriately.",
        "expected_patterns": [
            "kind: NetworkPolicy",
            "podSelector:",
            "ingress:",
            "from:",
            "namespaceSelector:",
            "ports:",
            "policyTypes:"
        ],
        "description": "Network policy for three-tier app with tier-to-tier isolation",
        "language": "yaml"
    },
    {
        "id": "k8s-012",
        "domain": "kubernetes",
        "difficulty": "expert",
        "prompt": "Write Kubernetes RBAC manifests for: (1) a ServiceAccount named 'ci-bot' in the 'ci' namespace, (2) a Role granting get, list, watch, create, update on pods and deployments in the 'ci' namespace, (3) a RoleBinding binding 'ci-bot' to that Role. Then write a ClusterRole that allows get/list on nodes and PVs across the cluster, and a ClusterRoleBinding granting this to 'ci-bot'. Include API group specifications.",
        "expected_patterns": [
            "kind: ServiceAccount",
            "kind: Role",
            "kind: RoleBinding",
            "kind: ClusterRole",
            "kind: ClusterRoleBinding",
            "apiGroups:",
            "resources:",
            "verbs:"
        ],
        "description": "RBAC: ServiceAccount, Role, RoleBinding, ClusterRole, ClusterRoleBinding",
        "language": "yaml"
    },
    {
        "id": "k8s-013",
        "domain": "kubernetes",
        "difficulty": "medium",
        "prompt": "Write a Namespace manifest for 'team-alpha' with labels (team: alpha, environment: development). Then write a ResourceQuota in that namespace that limits: pods to 10, services to 5, configmaps to 10, persistentvolumeclaims to 3, requests.cpu to 4, requests.memory to 8Gi, limits.cpu to 8, limits.memory to 16Gi. Then write a LimitRange that sets default CPU request to 100m, default memory request to 256Mi, and min/max constraints.",
        "expected_patterns": [
            "kind: Namespace",
            "kind: ResourceQuota",
            "hard:",
            "pods:",
            "requests.cpu:",
            "requests.memory:",
            "limits.cpu:",
            "kind: LimitRange",
            "default:",
            "defaultRequest:"
        ],
        "description": "Namespace with ResourceQuota and LimitRange for resource governance",
        "language": "yaml"
    },
    {
        "id": "k8s-014",
        "domain": "kubernetes",
        "difficulty": "hard",
        "prompt": "Write a PodDisruptionBudget manifest named 'api-pdb' for a deployment with app: api label. Ensure minAvailable is set to 2. Then write one with maxUnavailable set to 1 for a 'worker' deployment. Explain the difference between minAvailable and maxUnavailable. Show kubectl commands to check PDB status and list disruptions.",
        "expected_patterns": [
            "kind: PodDisruptionBudget",
            "minAvailable: 2",
            "maxUnavailable: 1",
            "selector:",
            "kubectl get pdb",
            "kubectl describe pdb"
        ],
        "description": "PodDisruptionBudget with minAvailable and maxUnavailable policies",
        "language": "yaml"
    },
    {
        "id": "k8s-015",
        "domain": "kubernetes",
        "difficulty": "hard",
        "prompt": "Write a Pod manifest with an init container named 'init-migrations' (image: myapp-migrations:latest) that runs database schema migrations. The main container 'app' (image: myapp:latest) should wait for the init container to complete successfully. Then add a sidecar container named 'sidecar-proxy' (image: envoyproxy/envoy:v1.28) alongside the main container. Both main and sidecar should share the same network namespace and a shared emptyDir volume for configuration.",
        "expected_patterns": [
            "initContainers:",
            "containers:",
            "image: myapp-migrations:latest",
            "image: envoyproxy/envoy:v1.28",
            "emptyDir:",
            "volumeMounts:",
            "shareProcessNamespace:"
        ],
        "description": "Init container for migrations and sidecar proxy pattern",
        "language": "yaml"
    },
    # ============================================================
    # CI/CD - GITHUB ACTIONS (001-015)
    # ============================================================
    {
        "id": "ci-001",
        "domain": "github_actions",
        "difficulty": "beginner",
        "prompt": "Write a GitHub Actions workflow that triggers on push to main and pull requests targeting main. Check out the code, set up Python 3.12, install dependencies from requirements.txt, run pytest, and upload test results as artifacts. Name the workflow 'CI Pipeline'. Use ubuntu-latest as the runner.",
        "expected_patterns": [
            "on:",
            "push:",
            "pull_request:",
            "branches: [main]",
            "actions/checkout@",
            "actions/setup-python@",
            "pytest",
            "actions/upload-artifact@"
        ],
        "description": "Basic CI workflow with Python setup, tests, and artifact upload",
        "language": "yaml"
    },
    {
        "id": "ci-002",
        "domain": "github_actions",
        "difficulty": "medium",
        "prompt": "Write a GitHub Actions workflow with a matrix build strategy. Test across Python versions 3.10, 3.11, 3.12 and operating systems ubuntu-latest, windows-latest. Use a fail-fast strategy with max-parallel of 4. Include a step that runs only on ubuntu and python 3.12 (using conditional). Name the job 'test'.",
        "expected_patterns": [
            "strategy:",
            "matrix:",
            "python-version:",
            "os:",
            "fail-fast:",
            "max-parallel: 4",
            "if: matrix.os"
        ],
        "description": "Matrix build across Python versions and OS platforms",
        "language": "yaml"
    },
    {
        "id": "ci-003",
        "domain": "github_actions",
        "difficulty": "medium",
        "prompt": "Write a GitHub Actions workflow for a Node.js project that implements dependency caching. Checkout the code, set up Node 20, cache node_modules using actions/cache with a key based on package-lock.json hash, run npm ci, and run npm test. Add a restore-keys fallback to the previous cache entry. Include a 'lint' job that runs ESLint.",
        "expected_patterns": [
            "actions/cache@",
            "key:",
            "restore-keys:",
            "hashFiles",
            "npm ci",
            "npm test",
            "npm run lint"
        ],
        "description": "Workflow with npm dependency caching and lint job",
        "language": "yaml"
    },
    {
        "id": "ci-004",
        "domain": "github_actions",
        "difficulty": "easy",
        "prompt": "Write a GitHub Actions workflow that builds a Docker image and uploads both the image and build artifacts. Use docker/build-push-action to build and tag the image. Then upload the built image as an artifact. Also upload test coverage reports (coverage.xml and htmlcov/) as separate artifacts. Name the workflow 'Build and Artifacts'.",
        "expected_patterns": [
            "docker/build-push-action@",
            "actions/upload-artifact@",
            "tags:",
            "coverage.xml",
            "htmlcov"
        ],
        "description": "Docker build and multi-artifact upload workflow",
        "language": "yaml"
    },
    {
        "id": "ci-005",
        "domain": "github_actions",
        "difficulty": "easy",
        "prompt": "Write a GitHub Actions workflow that demonstrates using secrets and environment variables. Create a job 'deploy' that runs on push to main. Set env vars LOG_LEVEL=info and APP_ENV=production at the workflow level. Use secrets called DOCKER_USERNAME and DOCKER_PASSWORD to log in to DockerHub. Use a GitHub environment called 'production' with a protection rule timeout of 30 minutes.",
        "expected_patterns": [
            "env:",
            "secrets:",
            "environment:",
            "LOG_LEVEL",
            "docker/login-action@",
            "timeout-minutes: 30"
        ],
        "description": "Secrets, environment variables, GitHub environments, and Docker login",
        "language": "yaml"
    },
    {
        "id": "ci-006",
        "domain": "github_actions",
        "difficulty": "hard",
        "prompt": "Write a reusable GitHub Actions workflow called 'deploy.yml' in .github/workflows/ that accepts inputs for environment (staging/production), image tag, and a boolean for whether to run migrations. It deploys to a Kubernetes cluster using kubectl with a kubeconfig secret. The workflow should have two jobs: 'migrate' (conditional on input) and 'deploy' (depends on migrate if it runs). Also write a caller workflow that calls this reusable workflow with staging params and the migration flag set to true.",
        "expected_patterns": [
            "on:",
            "workflow_call:",
            "inputs:",
            "secrets:",
            "jobs:",
            "uses: ./.github/workflows/deploy.yml",
            "with:",
            "kubectl set image"
        ],
        "description": "Reusable deployment workflow with conditional migration job and caller",
        "language": "yaml"
    },
    {
        "id": "ci-007",
        "domain": "github_actions",
        "difficulty": "hard",
        "prompt": "Write a composite GitHub Action that checks code quality. The action should: accept inputs for python-version (default 3.12) and fail-level (default warning). It should run black --check, ruff check, and mypy. Use the action in a workflow. The composite action should be in .github/actions/code-quality/action.yml.",
        "expected_patterns": [
            "runs:",
            "using: composite",
            "inputs:",
            "steps:",
            "black --check",
            "ruff check",
            "mypy"
        ],
        "description": "Composite action for Python code quality checks",
        "language": "yaml"
    },
    {
        "id": "ci-008",
        "domain": "github_actions",
        "difficulty": "medium",
        "prompt": "Write a GitHub Actions workflow that configures and uses a self-hosted runner. Set the workflow to run only on self-hosted runners with labels 'linux' and 'gpu'. Checkout code, verify the runner environment (env vars, hardware), run a GPU-dependent test script, and upload results. Add a cleanup step that always runs to free disk space.",
        "expected_patterns": [
            "runs-on: [self-hosted, linux, gpu]",
            "if: always()",
            "cleanup",
            "env:",
            "nvidia-smi"
        ],
        "description": "Self-hosted runner workflow with GPU verification and cleanup",
        "language": "yaml"
    },
    {
        "id": "ci-009",
        "domain": "github_actions",
        "difficulty": "beginner",
        "prompt": "Write a GitHub Actions workflow triggered on a schedule to run every hour for a data refresh job. Use cron syntax '0 * * * *'. Add a workflow_dispatch trigger as well. The job should check out code, run a Python script called 'refresh_data.py', and commit any changed data files back to the repo using a PAT stored in secrets. Set the timezone display to UTC.",
        "expected_patterns": [
            "schedule:",
            "cron:",
            "workflow_dispatch:",
            "git config",
            "git commit",
            "secrets.PAT"
        ],
        "description": "Scheduled workflow with cron trigger and auto-commit",
        "language": "yaml"
    },
    {
        "id": "ci-010",
        "domain": "github_actions",
        "difficulty": "easy",
        "prompt": "Write a GitHub Actions workflow that triggers on pull request events with specific label filtering. Trigger when a PR labeled 'deploy-staging' is opened, synchronized, or labeled. Run a deployment job that prints the PR number, head ref, and base ref. Use github.event context to access PR metadata. Add a PR comment with the deployment URL after job completion.",
        "expected_patterns": [
            "pull_request_target:",
            "types:",
            "labels:",
            "deploy-staging",
            "github.event.pull_request",
            "gh pr comment"
        ],
        "description": "PR-triggered workflow with label filter and PR comment",
        "language": "yaml"
    },
    {
        "id": "ci-011",
        "domain": "github_actions",
        "difficulty": "hard",
        "prompt": "Write a GitHub Actions workflow that implements deployment to GitHub Environments with OIDC (OpenID Connect) authentication to AWS. Configure permissions for id-token: write and contents: read. Use aws-actions/configure-aws-credentials with role-to-assume. Deploy to two environments: 'staging' (on push to develop) and 'production' (on push to main with manual approval via environment protection rules). Use environment URLs.",
        "expected_patterns": [
            "permissions:",
            "id-token: write",
            "configure-aws-credentials@",
            "role-to-assume:",
            "environment:",
            "deployment",
            "environment_urls:"
        ],
        "description": "OIDC-based deployment to AWS with staging and production environments",
        "language": "yaml"
    },
    {
        "id": "ci-012",
        "domain": "github_actions",
        "difficulty": "hard",
        "prompt": "Write a GitHub Actions workflow that demonstrates the use of service containers for integration testing. Define a PostgreSQL service container (image: postgres:16) and a Redis service container (image: redis:7-alpine). Configure PostgreSQL with env vars for POSTGRES_PASSWORD and POSTGRES_DB. Map ports 5432 and 6379. Run pytest with a database-dependent test suite. Add a health check for PostgreSQL before running tests.",
        "expected_patterns": [
            "services:",
            "postgres:",
            "redis:",
            "image: postgres:16",
            "options:",
            "--health-cmd",
            "ports:",
            "pytest"
        ],
        "description": "Service containers for PostgreSQL and Redis test dependencies",
        "language": "yaml"
    },
    {
        "id": "ci-013",
        "domain": "github_actions",
        "difficulty": "medium",
        "prompt": "Write a GitHub Actions workflow with multiple jobs in a dependency chain: 'lint' -> 'test' -> 'build' -> 'deploy'. The 'lint' and 'test' jobs run in parallel. 'build' depends on both. 'deploy' depends on 'build'. Use the 'needs' keyword. Add a 'build-artifact' step that uploads the dist/ folder. The 'deploy' job should download the artifact using actions/download-artifact.",
        "expected_patterns": [
            "needs:",
            "parallel",
            "actions/upload-artifact@",
            "actions/download-artifact@",
            "dist/"
        ],
        "description": "Multi-job workflow with parallel and sequential dependencies",
        "language": "yaml"
    },
    {
        "id": "ci-014",
        "domain": "github_actions",
        "difficulty": "medium",
        "prompt": "Write a GitHub Actions workflow that builds a Docker image, logs in to DockerHub using docker/login-action, and pushes the image using docker/build-push-action. Use semantic versioning tags: latest, and the short SHA (github.sha). Set up QEMU and Docker Buildx for multi-platform builds. Cache Docker layers to speed up subsequent builds.",
        "expected_patterns": [
            "docker/setup-qemu-action@",
            "docker/setup-buildx-action@",
            "docker/login-action@",
            "docker/build-push-action@",
            "cache-from:",
            "cache-to:",
            "push: true",
            "tags:"
        ],
        "description": "Docker build and push workflow with Buildx, QEMU, and layer caching",
        "language": "yaml"
    },
    {
        "id": "ci-015",
        "domain": "github_actions",
        "difficulty": "medium",
        "prompt": "Write a GitHub Actions workflow that uses a reusable workflow from a different repository (org/repo/.github/workflows/shared.yml@v1). Pass inputs for app-name and environment. Use a personal access token stored in secrets for authentication. The workflow should also define a fallback: if the reusable workflow fails, send a notification to Slack using a webhook URL from secrets.",
        "expected_patterns": [
            "uses:",
            "with:",
            "secrets:",
            "inherit",
            "if: failure()",
            "slack",
            "webhook"
        ],
        "description": "External reusable workflow from another repository with Slack notification on failure",
        "language": "yaml"
    },
    # ============================================================
    # GIT (001-010)
    # ============================================================
    {
        "id": "git-001",
        "domain": "git",
        "difficulty": "medium",
        "prompt": "Write a sequence of git commands implementing GitFlow branching model. Create a repository, initialize the main branch with an initial commit. Create a develop branch from main. Create a feature branch called 'feature/user-auth' from develop. Make changes, commit them, and merge back into develop. Then create a release branch 'release/v1.0.0' from develop. Finish the release by merging into main and tagging as v1.0.0. Show commands for hotfix branching as well.",
        "expected_patterns": [
            "git flow init",
            "git checkout -b develop",
            "git checkout -b feature/",
            "git checkout -b release/",
            "git tag",
            "git checkout -b hotfix/"
        ],
        "description": "GitFlow branching model: features, releases, hotfixes",
        "language": "bash"
    },
    {
        "id": "git-002",
        "domain": "git",
        "difficulty": "medium",
        "prompt": "Write a sequence of git commands demonstrating trunk-based development. Create a main branch. Make short-lived feature branches. Use feature flags instead of long-lived branches. Use git merge --squash to bring feature work into main with a single commit. Use short-lived release branches only for cherry-picking critical fixes. Show how to use git rebase to keep feature branches up to date with main before squashing.",
        "expected_patterns": [
            "git checkout -b",
            "git merge --squash",
            "git rebase",
            "git cherry-pick",
            "git branch -d"
        ],
        "description": "Trunk-based development with squash merges and short-lived branches",
        "language": "bash"
    },
    {
        "id": "git-003",
        "domain": "git",
        "difficulty": "medium",
        "prompt": "Write git commands for an interactive rebase workflow. Start with a branch that has 5 commits. Use git rebase -i HEAD~5 to: squash the first two commits into one, reword the third commit message, edit the fourth commit to fix a bug, and keep the fifth commit as is. Show how to continue the rebase after the edit step and how to abort if things go wrong.",
        "expected_patterns": [
            "git rebase -i HEAD~5",
            "squash",
            "reword",
            "edit",
            "git rebase --continue",
            "git rebase --abort"
        ],
        "description": "Interactive rebase to squash, reword, and edit commits",
        "language": "bash"
    },
    {
        "id": "git-004",
        "domain": "git",
        "difficulty": "easy",
        "prompt": "Write git commands demonstrating cherry-pick. Starting from a main branch, create two feature branches. Make commits on each. Cherry-pick a specific commit from feature-branch-a into feature-branch-b. Then cherry-pick a range of commits from feature-branch-b into main. Show how to handle cherry-pick conflicts (resolve and continue) and how to abort a cherry-pick.",
        "expected_patterns": [
            "git cherry-pick",
            "git cherry-pick --continue",
            "git cherry-pick --abort",
            "cherry-pick range"
        ],
        "description": "Cherry-pick single commit, commit range, and conflict resolution",
        "language": "bash"
    },
    {
        "id": "git-005",
        "domain": "git",
        "difficulty": "hard",
        "prompt": "Write git commands for a full git bisect session. Start a bisect session to find a commit that introduced a bug. Mark the current commit as bad and an old known-good commit as good. Use git bisect run with a test script that returns 0 for good and 1 for bad. Show how to manually test each bisect step. After finding the bad commit, reset the bisect and inspect the offending commit. Write a test script that can automate the bisect.",
        "expected_patterns": [
            "git bisect start",
            "git bisect bad",
            "git bisect good",
            "git bisect run",
            "git bisect reset",
            "git show"
        ],
        "description": "Git bisect to find the commit introducing a bug",
        "language": "bash"
    },
    {
        "id": "git-006",
        "domain": "git",
        "difficulty": "beginner",
        "prompt": "Write git stash commands demonstrating: stashing current changes (including untracked files), listing stashes, applying a specific stash (stash@{2}), popping the most recent stash, creating a stash with a descriptive message, stashing only staged changes, showing the diff of a stash without applying it, and dropping a specific stash. Explain the difference between git stash apply and git stash pop.",
        "expected_patterns": [
            "git stash",
            "git stash list",
            "git stash apply",
            "git stash pop",
            "git stash push -m",
            "git stash show",
            "git stash drop",
            "--include-untracked"
        ],
        "description": "Git stash: push, pop, apply, list, show, drop, untracked",
        "language": "bash"
    },
    {
        "id": "git-007",
        "domain": "git",
        "difficulty": "hard",
        "prompt": "Write git commands demonstrating git submodules workflow. Add a submodule (github.com/example/shared-lib) to a repository at path 'libs/shared'. Initialize and update submodules recursively. Clone a repository with submodules using --recurse-submodules. Pull the latest changes from all submodules. Show how to: change a submodule URL, update submodule to a specific commit, and remove a submodule completely.",
        "expected_patterns": [
            "git submodule add",
            "git submodule init",
            "git submodule update",
            "--recursive",
            "--recurse-submodules",
            "git submodule deinit"
        ],
        "description": "Git submodules: add, init, update, clone, change URL, remove",
        "language": "bash"
    },
    {
        "id": "git-008",
        "domain": "git",
        "difficulty": "medium",
        "prompt": "Write a pre-commit hook script (.git/hooks/pre-commit) that: runs black --check on staged Python files, runs ruff on staged files, prevents commits to main or master branches, checks for large files (>5MB) being committed, and verifies no trailing whitespace. Use git diff --cached to check staged files. Make the hook executable. Write the hook in bash.",
        "expected_patterns": [
            "#!/bin/bash",
            "git diff --cached",
            "black --check",
            "ruff",
            "branch=\"$(git rev-parse --abbrev-ref HEAD)\"",
            "main|master",
            "wc -c"
        ],
        "description": "Git pre-commit hook with linting, branch protection, and file size check",
        "language": "bash"
    },
    {
        "id": "git-009",
        "domain": "git",
        "difficulty": "hard",
        "prompt": "Write git worktree commands that demonstrate parallel development using worktrees. Create a new worktree at ../project-hotfix for a hotfix branch. Create another worktree at ../project-feature for a feature branch. Show all linked worktrees. Make commits in one worktree and verify the main working directory is unaffected. Show how to prune stale worktree references after deleting a branch. Explain the advantage of worktrees over git stash for multi-task workflows.",
        "expected_patterns": [
            "git worktree add",
            "git worktree list",
            "git worktree remove",
            "git worktree prune",
            "-B"
        ],
        "description": "Git worktree for parallel feature and hotfix development",
        "language": "bash"
    },
    {
        "id": "git-010",
        "domain": "git",
        "difficulty": "expert",
        "prompt": "Write git reflog commands to recover from common disasters. Show the reflog for HEAD and for a specific branch. Demonstrate recovering a commit that was lost after a hard reset (git reset --hard HEAD~3). Recover a deleted branch by finding its tip in reflog. Recover after an interactive rebase went wrong. Recover a dropped stash. Show how to expire reflog entries and explain the reflog retention policy (gc.reflogExpire).",
        "expected_patterns": [
            "git reflog",
            "git reflog show",
            "git reset --hard",
            "git branch",
            "git stash",
            "git reflog expire",
            "gc.reflogExpire"
        ],
        "description": "Git reflog recovery: lost commits, deleted branches, aborted rebase, dropped stash",
        "language": "bash"
    },
]
