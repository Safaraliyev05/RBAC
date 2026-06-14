# Running & Demonstrating the RBAC Platform

A single reference for running every part of the project and showing it to the jury.
Pick the section you need — they are independent.

---

## 0. Fastest live demo (cluster already deployed)

If the k3s deployment is already running, just start two port-forwards and open the URLs.

```bash
# Argo CD UI  → https://localhost:8080
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# RBAC app    → http://localhost:8081
kubectl port-forward svc/rbac-frontend -n rbac 8081:80 &
```

**Credentials**

```bash
# Argo CD admin password (username: admin)
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

| What | URL | Login |
|------|-----|-------|
| Argo CD (GitOps) | https://localhost:8080 | `admin` / *(command above)* |
| RBAC app | http://localhost:8081 | `admin@example.com` / `Admin@1234!` |

---

## 1. Local development (no containers)

**Backend** (Python 3.13+):
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                     # set a SECRET_KEY
python manage.py migrate
python manage.py seed_data               # roles + admin@example.com / Admin@1234!
python manage.py runserver 0.0.0.0:8000  # http://localhost:8000
```

**Frontend** (Node 20+), in a second terminal:
```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

---

## 2. Docker Compose (one command)

```bash
docker compose up --build
# backend  → http://localhost:8000
# frontend → http://localhost:8080
# seed once the backend is up:
docker compose exec backend python manage.py seed_data
```

Stop: `docker compose down` (add `-v` to also drop the database volume).

---

## 3. Kubernetes / k3s with Helm

```bash
# lint & preview
helm lint rbac
helm template rbac-platform rbac -n rbac

# install
helm install rbac-platform rbac -n rbac --create-namespace

# wait for pods, then seed the admin user
kubectl rollout status deploy/rbac-platform-backend -n rbac
kubectl exec -n rbac deploy/rbac-platform-backend -- python manage.py seed_data

# access the app
kubectl port-forward svc/rbac-frontend -n rbac 8081:80   # http://localhost:8081

# smoke test (chart's helm test)
helm test rbac-platform -n rbac
```

Upgrade after a change: `helm upgrade rbac-platform rbac -n rbac`
Uninstall: `helm uninstall rbac-platform -n rbac`

---

## 4. GitOps with Argo CD

**Install Argo CD:**
```bash
kubectl create namespace argocd
kubectl apply --server-side -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

**Deploy the platform via Argo (watches the `rbac/` Helm chart on `master`):**
```bash
kubectl apply -f - <<'YAML'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: rbac-platform
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Safaraliyev05/RBAC.git
    targetRevision: master
    path: rbac
  destination:
    server: https://kubernetes.default.svc
    namespace: rbac
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions: [CreateNamespace=true, ApplyOutOfSyncOnly=true]
YAML

# watch it sync, then seed
kubectl get application rbac-platform -n argocd -w   # Ctrl-C when Synced/Healthy
kubectl exec -n rbac deploy/rbac-platform-backend -- python manage.py seed_data

# open the Argo CD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

> The repo file `argocd/application.yaml` is the version-controlled copy (its
> `metadata.namespace` is set for an apps-in-any-namespace setup). The inline
> manifest above targets the default `argocd` namespace, which works out of the box.

---

## 5. CI/CD (GitHub Actions → Docker Hub)

Push to `master` triggers both workflows automatically:

| Workflow | Does |
|----------|------|
| `ci.yml` | backend `pytest` + frontend build |
| `docker-build.yml` | build & push `safaral1yev05/rbac-backend` and `rbac-frontend` to Docker Hub |

`docker-build.yml` needs two repo secrets (Settings → Secrets and variables → Actions):
`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

Build & push images manually (no CI):
```bash
docker login -u safaral1yev05
docker build -t safaral1yev05/rbac-backend:latest  ./backend  && docker push safaral1yev05/rbac-backend:latest
docker build -t safaral1yev05/rbac-frontend:latest ./frontend && docker push safaral1yev05/rbac-frontend:latest
```

---

## 6. Run the tests

```bash
cd backend
pytest                       # 33 tests: auth/lockout, RBAC discovery/aggregation/enforcement, audit
# or, without pytest:
python manage.py test apps
```

---

## 7. Status checks (handy while presenting)

```bash
kubectl get all -n rbac                                   # workloads
kubectl get application rbac-platform -n argocd \
  -o custom-columns='APP:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status'
helm list -n rbac                                         # the release
kubectl logs -n rbac deploy/rbac-platform-backend --tail=20
curl -k https://localhost:8080/ -o /dev/null -w 'argocd %{http_code}\n'
curl http://localhost:8081/api/auth/profile/ -o /dev/null -w 'api %{http_code}\n'   # 401 = working
```

---

## 8. Default credentials

| System | User | Password |
|--------|------|----------|
| RBAC app | `admin@example.com` | `Admin@1234!` |
| Argo CD | `admin` | retrieve from `argocd-initial-admin-secret` (see §0) |

Roles seeded: **Admin** (all permissions), **Auditor** (read + audit/reports), **User** (own profile only).

---

## 9. Teardown

```bash
# kill port-forwards
pkill -f 'port-forward'

# remove the app
kubectl delete application rbac-platform -n argocd     # Argo-managed
# or
helm uninstall rbac-platform -n rbac                   # Helm-managed

# remove Argo CD + namespaces (optional)
kubectl delete namespace argocd rbac
```
