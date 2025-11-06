# Market Assistant Agent - GKE Deployment Guide

This guide provides step-by-step instructions for deploying the LangGraph Market Assistant Agent to Google Kubernetes Engine (GKE).

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Build](#docker-build)
- [GKE Deployment](#gke-deployment)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- **Google Cloud SDK** (`gcloud`) - [Install](https://cloud.google.com/sdk/docs/install)
- **Docker** - [Install](https://docs.docker.com/get-docker/)
- **kubectl** - Kubernetes CLI (comes with gcloud)
- **Python 3.11+** - For local testing

### Required API Keys
1. **OpenAI API Key** - [Get it here](https://platform.openai.com/api-keys)
2. **Tavily API Key** - [Get it here](https://tavily.com/)
3. **Alpha Vantage API Key** - [Get it here](https://www.alphavantage.co/support/#api-key)
4. **LangSmith API Key** (Optional) - [Get it here](https://smith.langchain.com/)

### GCP Setup
```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  container.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## Local Development

### 1. Setup Environment

```bash
# Navigate to the agent directory
cd hz_langgraph_learning/agent-dev

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=sk-...
# TAVILY_API_KEY=tvly-...
# ALPHAVANTAGE_API_KEY=...
```

### 3. Test Locally

```bash
# Run the FastAPI server
python api.py

# In another terminal, test the API
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Tesla stock price?",
    "output_mode": "voice"
  }'
```

### 4. Test with Interactive Chat (Optional)

```bash
# Run the CLI interface
python chat.py

# Or with debug mode
python chat.py --debug
```

---

## Docker Build

### 1. Build Docker Image Locally

```bash
# Build the image
docker build -t market-assistant:latest .

# Test the image locally
docker run -p 8080:8080 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e TAVILY_API_KEY="$TAVILY_API_KEY" \
  -e ALPHAVANTAGE_API_KEY="$ALPHAVANTAGE_API_KEY" \
  market-assistant:latest

# Test in another terminal
curl http://localhost:8080/health
```

### 2. Push to Google Container Registry

```bash
# Tag the image for GCR
docker tag market-assistant:latest gcr.io/$PROJECT_ID/market-assistant:latest

# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Push to GCR
docker push gcr.io/$PROJECT_ID/market-assistant:latest
```

### 3. Alternative: Build with Google Cloud Build

```bash
# Build directly on GCP (faster for large images)
gcloud builds submit --tag gcr.io/$PROJECT_ID/market-assistant:latest .
```

---

## GKE Deployment

### 1. Create GKE Cluster

```bash
# Create a GKE cluster (standard or autopilot)
gcloud container clusters create market-assistant-cluster \
  --zone us-central1-a \
  --num-nodes 2 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 5

# Get cluster credentials
gcloud container clusters get-credentials market-assistant-cluster --zone us-central1-a
```

### 2. Configure Secrets

**Option A: Using Kubernetes Secrets (Quick)**
```bash
# Create namespace
kubectl create namespace market-assistant

# Create secrets
kubectl create secret generic market-assistant-secrets \
  --namespace=market-assistant \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=TAVILY_API_KEY="$TAVILY_API_KEY" \
  --from-literal=ALPHAVANTAGE_API_KEY="$ALPHAVANTAGE_API_KEY" \
  --from-literal=LANGSMITH_API_KEY="$LANGSMITH_API_KEY"
```

**Option B: Using Google Secret Manager (Recommended for Production)**
```bash
# Create secrets in Secret Manager
echo -n "$OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
echo -n "$TAVILY_API_KEY" | gcloud secrets create tavily-api-key --data-file=-
echo -n "$ALPHAVANTAGE_API_KEY" | gcloud secrets create alphavantage-api-key --data-file=-

# Then configure workload identity to access these secrets
# See: https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity
```

### 3. Update Deployment Configuration

Edit `kubernetes-deployment.yaml`:
- Replace `YOUR_PROJECT_ID` with your actual GCP project ID
- Adjust resource limits based on your workload
- Configure ingress if needed

### 4. Deploy to GKE

```bash
# Apply the deployment
kubectl apply -f kubernetes-deployment.yaml

# Wait for deployment to be ready
kubectl wait --for=condition=available --timeout=300s \
  deployment/market-assistant -n market-assistant

# Check deployment status
kubectl get pods -n market-assistant
kubectl get services -n market-assistant
```

### 5. Get External IP

```bash
# Get the external IP of the LoadBalancer
kubectl get service market-assistant-service -n market-assistant

# Wait for EXTERNAL-IP to be assigned (may take a few minutes)
# You can also use:
kubectl get service market-assistant-service -n market-assistant --watch
```

---

## Testing

### 1. Health Check

```bash
# Get the external IP
export EXTERNAL_IP=$(kubectl get service market-assistant-service -n market-assistant -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl http://$EXTERNAL_IP/health
```

### 2. Test Chat API

```bash
# Test price check
curl -X POST http://$EXTERNAL_IP/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Tesla stock price?",
    "output_mode": "voice"
  }'

# Test news search
curl -X POST http://$EXTERNAL_IP/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest news on Apple",
    "output_mode": "voice"
  }'

# Test comparison
curl -X POST http://$EXTERNAL_IP/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare NVDA and AMD",
    "output_mode": "text"
  }'
```

### 3. Load Testing

```bash
# Install Apache Bench (if not already installed)
# Ubuntu: sudo apt-get install apache2-utils
# Mac: brew install apache2-utils

# Run load test
ab -n 100 -c 10 \
  -p request.json \
  -T "application/json" \
  http://$EXTERNAL_IP/chat

# Create request.json:
echo '{"query": "What is TSLA price?", "output_mode": "voice"}' > request.json
```

---

## Monitoring

### 1. View Logs

```bash
# Stream logs from all pods
kubectl logs -f -l app=market-assistant -n market-assistant

# View logs from specific pod
kubectl logs <pod-name> -n market-assistant

# View logs with timestamps
kubectl logs -f -l app=market-assistant -n market-assistant --timestamps
```

### 2. Check Pod Status

```bash
# Get pod status
kubectl get pods -n market-assistant

# Describe pod for detailed info
kubectl describe pod <pod-name> -n market-assistant

# Get resource usage
kubectl top pods -n market-assistant
```

### 3. Monitor Autoscaling

```bash
# Check HPA status
kubectl get hpa -n market-assistant

# Watch HPA in real-time
kubectl get hpa -n market-assistant --watch
```

### 4. Google Cloud Monitoring (Optional)

```bash
# Enable Google Cloud Operations for GKE
gcloud container clusters update market-assistant-cluster \
  --enable-cloud-logging \
  --enable-cloud-monitoring \
  --zone us-central1-a

# View logs in Cloud Console
# https://console.cloud.google.com/logs
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n market-assistant

# Common issues:
# - ImagePullBackOff: Check image name and GCR permissions
# - CrashLoopBackOff: Check application logs
# - Pending: Check resource availability
```

### API Key Issues

```bash
# Verify secrets are created
kubectl get secrets -n market-assistant

# Check secret contents (base64 encoded)
kubectl get secret market-assistant-secrets -n market-assistant -o yaml

# Delete and recreate if needed
kubectl delete secret market-assistant-secrets -n market-assistant
# Then recreate using the commands in step 2
```

### High Memory/CPU Usage

```bash
# Check resource usage
kubectl top pods -n market-assistant

# If consistently high, increase resource limits in kubernetes-deployment.yaml:
# resources:
#   limits:
#     memory: "4Gi"
#     cpu: "2000m"

# Then apply the changes
kubectl apply -f kubernetes-deployment.yaml
```

### Playwright Browser Issues

```bash
# If Playwright fails to launch browsers, check:
# 1. Make sure Dockerfile has all browser dependencies
# 2. Check pod logs for missing libraries
# 3. Try running with --no-sandbox flag (add to Playwright config)
```

### Network Issues

```bash
# Test internal connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n market-assistant -- sh

# Inside the debug pod:
curl http://market-assistant-service/health

# Test external API connectivity
curl https://api.openai.com/v1/models
```

---

## Cleanup

### Delete Deployment

```bash
# Delete all resources
kubectl delete namespace market-assistant

# Or delete specific resources
kubectl delete -f kubernetes-deployment.yaml
```

### Delete GKE Cluster

```bash
# Delete the cluster
gcloud container clusters delete market-assistant-cluster --zone us-central1-a
```

### Delete Docker Images

```bash
# List images in GCR
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Delete specific image
gcloud container images delete gcr.io/$PROJECT_ID/market-assistant:latest --quiet
```

---

## Production Best Practices

1. **Use Workload Identity**: Instead of Kubernetes secrets, use GCP Workload Identity to access Secret Manager
2. **Enable HTTPS**: Configure Ingress with managed SSL certificates
3. **Set up CI/CD**: Use Cloud Build or GitHub Actions for automated deployments
4. **Configure Monitoring**: Set up alerting in Google Cloud Monitoring
5. **Enable Logging**: Forward logs to Cloud Logging for analysis
6. **Use VPC**: Deploy GKE in a private VPC for better security
7. **Resource Limits**: Set appropriate CPU/memory limits based on load testing
8. **Rate Limiting**: Implement rate limiting at the API level
9. **Caching**: Enable caching for frequently requested data
10. **Backup**: Backup any persistent data regularly

---

## API Documentation

Once deployed, you can access the interactive API documentation at:
- **Swagger UI**: `http://$EXTERNAL_IP/docs`
- **ReDoc**: `http://$EXTERNAL_IP/redoc`

---

## Support

For issues and questions:
- Check application logs: `kubectl logs -l app=market-assistant -n market-assistant`
- Review GKE documentation: https://cloud.google.com/kubernetes-engine/docs
- LangGraph documentation: https://langchain-ai.github.io/langgraph/

---

**Last Updated**: 2025-11-06
