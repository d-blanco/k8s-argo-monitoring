# Monitoring Stack Deployment

Quick setup guide for deploying the monitoring stack on EKS with ArgoCD.

## 1. Deploy EKS with Terraform

```bash
cd apps/terraform

terraform init
terraform plan
terraform apply
```

## 2. Configure kubectl

```bash
aws eks update-kubeconfig --name monitoring-lab --region us-east-1
```

Verify:
```bash
kubectl get nodes
```

## 3. Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
```

Get ArgoCD admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

## 4. Deploy App of Apps

```bash
kubectl apply -f apps/argocd-apps.yaml
```

This deploys all applications:
- Prometheus, Loki, Grafana, Tempo (monitoring)
- k8s-monitoring (Alloy collectors)
- MySQL, Redis (databases)
- FastAPI (sample app)

Watch sync status:
```bash
kubectl get applications -n argocd
```

## 5. Get Endpoints

### Grafana
```bash
kubectl get svc grafana-lb -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```
Default credentials: `admin` / `admin`

### FastAPI
```bash
kubectl get svc fastapi-lb -n fastapi -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### ArgoCD UI
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
Open: https://localhost:8080

## Directory Structure

```
apps/
├── argocd-apps.yaml      # Parent App of Apps
├── argocd-apps/          # Individual ArgoCD Application manifests
├── terraform/            # EKS infrastructure
├── prometheus/           # Prometheus Helm wrapper
├── loki/                 # Loki Helm wrapper
├── grafana/              # Grafana Helm wrapper
├── tempo/                # Tempo Helm wrapper
├── k8s-monitoring/       # Alloy collectors
├── mysql/                # MySQL + exporter
├── redis/                # Redis + exporter
└── fastapi/              # Sample FastAPI app
```
