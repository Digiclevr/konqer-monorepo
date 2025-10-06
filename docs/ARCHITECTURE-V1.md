# KONQER - Architecture V1 (Production Ready)

**Date:** 6 Octobre 2025
**Auteur:** Architecture Team
**Status:** Production Blueprint
**Objectif:** Lancement 12 services B2B + Founding Members (699€/an)

---

## 🎯 VISION & STRATÉGIE

### Modèle Commercial

**Vente Individuelle (Post-Founding) :**
- Chaque service vendu séparément → **99€/mois** (standalone)
- Bundle 12 services → **399€/mois** (réduction 67%)

**Offre Founding Members (Phase 1 - FOMO) :**
- **699€/an** → Accès aux 12 services
- Rolling unlock : 3 services live J1, 9 débloqués progressivement (4 semaines)
- Objectif : 43+ ventes × 699€ = **30k€+ ARR**

**Cross-Sell Progressif :**
- User achète service A → Email automatique propose service B (complémentaire)
- User achète 2-3 services → Proposition upgrade bundle (économie 40%)

---

## 🏗️ ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────────┐
│           FRONTEND (Kinsta Static CDN - Global)             │
├─────────────────────────────────────────────────────────────┤
│  konqer.app (site principal)                                │
│  + 12 sous-domaines (cold-dm.konqer.app, etc.)             │
│                                                             │
│  Stack: Next.js 14 App Router + Tailwind CSS               │
│  Build: Static Export (next export)                        │
│  Deploy: GitHub Actions → Kinsta auto-deploy               │
└─────────────────────────────────────────────────────────────┘
                          ↓ HTTPS/API calls
┌─────────────────────────────────────────────────────────────┐
│         KONG API GATEWAY (BlueOcean K8s - platform)         │
│                    api.konqer.app                           │
├─────────────────────────────────────────────────────────────┤
│  Routes:                                                    │
│    /auth/*   → Keycloak (JWT generation)                   │
│    /api/*    → konqer-api-backend (saas node-pool)         │
│    /admin/*  → konqer-admin-backend (IP filtered)          │
│                                                             │
│  Plugins: JWT validation, Rate limiting, CORS, Logging     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│       KEYCLOAK (Auth Service - platform node-pool)          │
├─────────────────────────────────────────────────────────────┤
│  Realm: konqer                                              │
│  OAuth2: GitHub, Google, LinkedIn                           │
│  JWT: RS256, 1h expiry                                      │
│  Roles: user, founding_member, admin                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│      KONQER API BACKEND (FastAPI - saas node-pool)          │
│         Service: konqer-api-svc.saas:8000                   │
├─────────────────────────────────────────────────────────────┤
│  Routes: /user/*, /services/*, /checkout/*, /webhooks/*    │
│  Logic: OpenAI GPT-4o + Apollo API + LinkedIn API          │
│  Database: Postgres central (platform node-pool)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│    KONQER ADMIN BACKEND (FastAPI - saas node-pool)          │
│       Service: konqer-admin-svc.saas:8001                   │
│       Access: Port-forward ONLY (internal)                  │
├─────────────────────────────────────────────────────────────┤
│  Routes: /admin/metrics/*, /admin/users/*, /admin/services/*│
│  Features: MRR/ARR analytics, User management, Configs     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│      POSTGRES (platform node-pool - postgres-central)       │
│    postgres-central.platform.svc.cluster.local:5432         │
│              Database: konqer_production                    │
├─────────────────────────────────────────────────────────────┤
│  Tables: users, subscriptions, service_access, generations, │
│          service_configs, payments, admin_users, events     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 SCHEMA DATABASE (Postgres Unique)

### Tables Core

```sql
-- ============================================
-- USERS & AUTH
-- ============================================
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  stripe_customer_id VARCHAR UNIQUE,
  keycloak_user_id VARCHAR UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);

-- ============================================
-- SUBSCRIPTIONS & PAYMENTS
-- ============================================
CREATE TYPE subscription_plan AS ENUM (
  'founding',
  'monthly_single',
  'monthly_bundle',
  'annual_single',
  'annual_bundle'
);

CREATE TYPE subscription_status AS ENUM (
  'active',
  'canceled',
  'past_due',
  'unpaid',
  'trialing'
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  plan subscription_plan NOT NULL,
  status subscription_status NOT NULL DEFAULT 'active',
  stripe_subscription_id VARCHAR UNIQUE,
  current_period_start TIMESTAMP,
  current_period_end TIMESTAMP,
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

-- Service access (Founding Members rolling unlock)
CREATE TABLE service_access (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  service VARCHAR NOT NULL,
  unlocked_at TIMESTAMP DEFAULT NOW(),
  locked BOOLEAN DEFAULT false,
  UNIQUE(user_id, service)
);

CREATE INDEX idx_service_access_user ON service_access(user_id);

-- Payments history
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  stripe_payment_intent_id VARCHAR UNIQUE,
  amount INTEGER NOT NULL,  -- Centimes (69900 = 699€)
  currency VARCHAR(3) DEFAULT 'eur',
  status VARCHAR NOT NULL,
  subscription_id UUID REFERENCES subscriptions(id),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_created ON payments(created_at DESC);

-- ============================================
-- SERVICES GENERATIONS
-- ============================================
CREATE TABLE generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  service VARCHAR NOT NULL,
  prompt TEXT,
  output TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_generations_user_service ON generations(user_id, service, created_at DESC);
CREATE INDEX idx_generations_created ON generations(created_at DESC);

-- ============================================
-- SERVICE CONFIGS
-- ============================================
CREATE TABLE service_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service VARCHAR UNIQUE NOT NULL,
  name VARCHAR NOT NULL,
  slug VARCHAR UNIQUE NOT NULL,
  type VARCHAR,  -- 'Blue', 'Red', 'Core'
  pricing_monthly INTEGER,
  pricing_annual INTEGER,
  rate_limit_daily INTEGER DEFAULT 100,
  enabled BOOLEAN DEFAULT true,
  config JSONB,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed 12 services
INSERT INTO service_configs (service, name, slug, type, pricing_monthly, pricing_annual) VALUES
  ('cold-dm', 'Cold DM Personalizer', 'cold-dm-personalizer', 'Blue', 9900, 99000),
  ('battlecards', 'Outbound Battlecards AI', 'outbound-battlecards-ai', 'Blue', 9900, 99000),
  ('objection', 'Sales Objection Crusher', 'sales-objection-crusher', 'Blue', 9900, 99000),
  ('community-finder', 'Community Finder Pro', 'community-finder-pro', 'Blue', 9900, 99000),
  ('carousel', 'LinkedIn Carousel Forge', 'linkedin-carousel-forge', 'Blue', 9900, 99000),
  ('cold-email', 'AI Cold Email Writer', 'ai-cold-email-writer', 'Red', 9900, 99000),
  ('pitch-deck', 'Startup Pitch Deck Builder', 'startup-pitch-deck-builder', 'Core', 9900, 99000),
  ('whitepaper', 'AI Whitepaper Generator', 'ai-whitepaper-generator', 'Core', 9900, 99000),
  ('deck-heatmap', 'VC Deck Heatmap', 'vc-deck-heatmap', 'Blue', 9900, 99000),
  ('webinar', 'Webinar Demand Scanner', 'webinar-demand-scanner', 'Blue', 9900, 99000),
  ('warmranker', 'Email WarmRanker', 'email-warmranker', 'Red', 9900, 99000),
  ('no-show-shield', 'Calendar No-Show Shield', 'calendar-no-show-shield', 'Blue', 9900, 99000);

-- ============================================
-- ADMIN & INTERNAL
-- ============================================
CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR UNIQUE NOT NULL,
  role VARCHAR NOT NULL,  -- 'superadmin', 'support', 'finance'
  keycloak_user_id VARCHAR UNIQUE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE feature_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  flag_key VARCHAR UNIQUE NOT NULL,
  enabled BOOLEAN DEFAULT false,
  rollout_percentage INTEGER DEFAULT 100,
  config JSONB,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- ANALYTICS & TRACKING
-- ============================================
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  event_type VARCHAR NOT NULL,
  service VARCHAR,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_type_created ON events(event_type, created_at DESC);
CREATE INDEX idx_events_user ON events(user_id, created_at DESC);
```

---

## 🔧 STACK TECHNIQUE DÉTAILLÉE

### Frontend (Kinsta Static)

**Technologies :**
- Next.js 14.2.4 (App Router)
- React 18
- Tailwind CSS 3.4.17 (STABLE - pas v4)
- TypeScript 5+
- Lucide React (icons)

**Configuration :**
```javascript
// next.config.js
const nextConfig = {
  output: 'export',  // Static export obligatoire
  images: { unoptimized: true },
  trailingSlash: true,
  distDir: 'out'
};
```

**Déploiement :**
- GitHub Actions build → Push repo dédié → Kinsta auto-deploy
- CDN global (latence <50ms)
- SSL auto (Let's Encrypt)

### Backend API (FastAPI - saas node-pool)

**Technologies :**
- Python 3.11
- FastAPI 0.104+
- SQLAlchemy 2.0 (async)
- Pydantic v2
- asyncpg (Postgres async driver)
- OpenAI Python SDK 1.3+
- Stripe Python SDK 7.0+

**Structure :**
```
apps/api/
├── main.py
├── routers/
│   ├── auth.py
│   ├── user.py
│   ├── services.py
│   ├── admin.py
│   └── webhooks.py
├── models/
│   └── database.py
├── services/
│   ├── openai_service.py
│   ├── apollo_service.py
│   ├── linkedin_service.py
│   ├── stripe_service.py
│   └── auth_service.py
├── schemas/
│   └── api.py
└── requirements.txt
```

**Ports :**
- Développement local : 4000
- Production K8s : 8000 (container port)

### Backend Admin (FastAPI - saas node-pool)

**Accès :** Port-forward uniquement (pas de public ingress)

```bash
# Accès admin (exemple)
kubectl port-forward -n saas svc/konqer-admin-svc 8001:8001
# URL: http://localhost:8001/admin/metrics/mrr
```

**Sécurité :**
- IP whitelist (Kong level)
- JWT role check (role:admin requis)
- Basic Auth layer (optionnel)

### Infrastructure K8s (BlueOcean Cluster)

**Node-pools utilisés :**
- **platform** : Postgres, Redis, Kong, Keycloak
- **saas** : konqer-api-backend, konqer-admin-backend

**Secrets :**
- Stockage : DigitalOcean Secrets Manager
- Montage : External Secrets Operator

**Build Images :**
- Kaniko (in-cluster builds)
- Registry : registry.digitalocean.com/konqer/

---

## 🚀 SERVICES MÉTIER - LOGIQUE PREMIUM

### Service 1 : Cold DM Personalizer

**APIs Intégrées :**
- Apollo.io (enrichment profil contact)
- LinkedIn API (activité récente, posts)
- OpenAI GPT-4o (génération personnalisée)

**Flow :**
1. User input : Nom + Entreprise + LinkedIn URL
2. Apollo enrichment → Email, téléphone, tech stack, taille entreprise
3. LinkedIn scraping → Posts récents, commentaires, intérêts
4. GPT-4o génération → Message 100-150 mots, personnalisé
5. Scoring personnalisation → 0-100 (algorithme custom)

**Output :**
```json
{
  "message": "Hi John, I saw your recent post about...",
  "personalization_score": 87,
  "context_used": {
    "recent_activity": [...],
    "tech_stack": ["Salesforce", "HubSpot"],
    "company_size": 250
  },
  "enrichment_sources": ["apollo", "linkedin"]
}
```

### Service 2 : Sales Objection Crusher

**Base de données objections :**
- 50+ patterns objections (prix, timing, concurrent, autorité)
- Frameworks : Cost vs Value, Urgency Creation, Social Proof

**Flow :**
1. User input : Texte objection + contexte deal
2. Classification NLP → Type objection
3. Query database → Framework + case studies
4. GPT-4o génération → Réponse structurée (Empathy + Reframe + Evidence + Action)

**Output :**
```json
{
  "response": "I completely understand your concern about timing...",
  "objection_type": "timing",
  "framework_used": "Urgency Creation",
  "case_study_id": "uuid-123"
}
```

### Service 3 : LinkedIn Carousel Forge

**Fonctionnalités :**
- Génération 10 slides structurées
- Research topic (web search API)
- Suggestions visuelles (DALL-E 3 prompts)
- Export Canva (API integration)

**Flow :**
1. User input : Topic + Audience cible
2. Web research → Données récentes, trends
3. GPT-4o → Structure 10 slides (hook, body, CTA)
4. DALL-E 3 → Prompts visuels par slide
5. Canva API → Export template éditable

**Output :**
```json
{
  "slides": [
    {
      "title": "The Hidden Cost of Manual Prospecting",
      "content": "...",
      "visual_prompt": "minimalist illustration of..."
    }
  ],
  "canva_edit_link": "https://canva.com/design/xyz",
  "estimated_reach": 5000
}
```

### Services 4-12 : Patterns Similaires

Chaque service suit la même architecture :
- **Input enrichment** (APIs externes)
- **GPT-4o generation** (prompts optimisés)
- **Output structuré** (JSON + metadata)
- **Tracking** (events table)

---

## 🔐 AUTHENTIFICATION & AUTORISATION

### Flow OAuth2 (Keycloak)

```
1. User clique "Login with GitHub" sur konqer.app
   ↓
2. Redirect vers Keycloak
   https://auth.konqer.app/realms/konqer/protocol/openid-connect/auth
   ↓
3. User autorise GitHub OAuth
   ↓
4. Callback Keycloak → Créer/Update user
   ↓
5. JWT généré (RS256)
   {
     "sub": "keycloak-user-id",
     "email": "user@example.com",
     "roles": ["user"],
     "exp": 1696348800
   }
   ↓
6. Redirect konqer.app/dashboard?token=jwt_xxx
   ↓
7. Frontend stocke JWT (localStorage ou cookie httpOnly)
   ↓
8. API calls incluent header:
   Authorization: Bearer jwt_xxx
```

### Vérification Backend

```python
# FastAPI dependency
from fastapi import Depends, HTTPException
from jose import jwt, JWTError

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
            token,
            KEYCLOAK_PUBLIC_KEY,
            algorithms=["RS256"],
            audience="konqer-api"
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401)

        # Fetch user from DB
        user = await db.get_user_by_keycloak_id(user_id)
        return user
    except JWTError:
        raise HTTPException(401, "Invalid token")
```

---

## 💳 PAIEMENTS & WEBHOOKS STRIPE

### Checkout Flow

```python
# POST /checkout/founding
@router.post("/checkout/founding")
async def checkout_founding(current_user: User = Depends(get_current_user)):
    session = stripe.checkout.Session.create(
        customer=current_user.stripe_customer_id,
        payment_method_types=['card', 'paypal'],
        line_items=[{
            'price': 'price_1Abc...XYZ',  # Créé dans Stripe Dashboard
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://konqer.app/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://konqer.app/pricing',
        metadata={'user_id': str(current_user.id)}
    )
    return {"checkout_url": session.url}
```

### Webhook Handler

```python
# POST /webhooks/stripe
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get('stripe-signature')

    event = stripe.Webhook.construct_event(
        payload, sig, settings.STRIPE_WEBHOOK_SECRET
    )

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']

        # Create subscription
        await db.create_subscription(
            user_id=user_id,
            plan='founding',
            stripe_subscription_id=session['subscription'],
            current_period_end=datetime.fromtimestamp(session['expires_at'])
        )

        # Unlock initial 3 services
        await db.unlock_services(user_id, ['cold-dm', 'objection', 'carousel'])

        # Send welcome email
        await send_email(user_id, 'founding_welcome')

        # Track event
        await db.track_event(user_id, 'purchase', 'founding', {'amount': 69900})

    elif event['type'] == 'customer.subscription.deleted':
        # Handle cancellation
        pass

    return {"status": "success"}
```

---

## 📦 DÉPLOIEMENT K8S

### Namespace

```yaml
# k8s/namespaces/konqer.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: konqer
  labels:
    name: konqer
    environment: production
```

### API Backend Deployment

```yaml
# k8s/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: konqer-api
  namespace: saas
spec:
  replicas: 3
  selector:
    matchLabels:
      app: konqer-api
  template:
    metadata:
      labels:
        app: konqer-api
    spec:
      nodeSelector:
        node-pool: saas
      containers:
      - name: api
        image: registry.digitalocean.com/konqer/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: database-url
        - name: STRIPE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: stripe-secret
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: openai-key
        - name: APOLLO_API_KEY
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: apollo-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: konqer-api-svc
  namespace: saas
spec:
  selector:
    app: konqer-api
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### Kong Route Configuration

```yaml
# k8s/kong/konqer-routes.yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: konqer-jwt
  namespace: saas
plugin: jwt
config:
  uri_param_names:
    - jwt
  claims_to_verify:
    - exp
  key_claim_name: kid
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: konqer-rate-limit
  namespace: saas
plugin: rate-limiting
config:
  minute: 60
  policy: redis
  redis_host: platform-pool-redis-master.platform
  redis_port: 6379
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: konqer-api-ingress
  namespace: saas
  annotations:
    konghq.com/plugins: konqer-jwt,konqer-rate-limit
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: kong
  tls:
  - hosts:
    - api.konqer.app
    secretName: api-konqer-tls
  rules:
  - host: api.konqer.app
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: konqer-api-svc
            port:
              number: 8000
```

---

## 🔄 CI/CD PIPELINE

### GitHub Actions - API Backend

```yaml
# .github/workflows/deploy-api.yml
name: Deploy API Backend
on:
  push:
    branches: [main]
    paths:
      - 'apps/api/**'
      - '.github/workflows/deploy-api.yml'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to DigitalOcean Registry
      uses: docker/login-action@v2
      with:
        registry: registry.digitalocean.com
        username: ${{ secrets.DO_REGISTRY_TOKEN }}
        password: ${{ secrets.DO_REGISTRY_TOKEN }}

    - name: Build and push image (Kaniko alternative local)
      run: |
        docker build \
          -t registry.digitalocean.com/konqer/api:${{ github.sha }} \
          -t registry.digitalocean.com/konqer/api:latest \
          -f apps/api/Dockerfile \
          apps/api
        docker push registry.digitalocean.com/konqer/api:${{ github.sha }}
        docker push registry.digitalocean.com/konqer/api:latest

    - name: Setup kubectl
      uses: azure/setup-kubectl@v3

    - name: Deploy to K8s
      env:
        KUBECONFIG_DATA: ${{ secrets.KUBECONFIG_BASE64 }}
      run: |
        echo "$KUBECONFIG_DATA" | base64 -d > kubeconfig
        export KUBECONFIG=./kubeconfig

        kubectl set image deployment/konqer-api \
          api=registry.digitalocean.com/konqer/api:${{ github.sha }} \
          -n saas

        kubectl rollout status deployment/konqer-api -n saas
```

### GitHub Actions - Frontend (Kinsta)

```yaml
# .github/workflows/deploy-frontend-web.yml
name: Deploy Frontend Web
on:
  push:
    branches: [main]
    paths:
      - 'apps/web/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - uses: pnpm/action-setup@v2
      with:
        version: 8

    - uses: actions/setup-node@v3
      with:
        node-version: 20
        cache: 'pnpm'

    - name: Install dependencies
      run: pnpm install --frozen-lockfile

    - name: Build
      run: pnpm --filter=konqer-app build

    - name: Push to Kinsta repo
      run: |
        cd apps/web/out
        git init
        git config user.name "GitHub Actions"
        git config user.email "actions@github.com"
        git add .
        git commit -m "Deploy ${{ github.sha }}"
        git push --force https://x-access-token:${{ secrets.KINSTA_GITHUB_TOKEN }}@github.com/Digiclevr/konqer-web.git main
```

---

## 📊 MONITORING & OBSERVABILITY

### Prometheus Metrics (API Backend)

```python
# FastAPI middleware
from prometheus_client import Counter, Histogram, generate_latest

requests_total = Counter('konqer_api_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('konqer_api_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.observe(duration)
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Grafana Dashboards

**Accès :** http://grafana.monitoring.svc.cluster.local

**Dashboards Konqer :**
- API Requests (QPS, latency, errors)
- Database connections (pool usage, slow queries)
- Business metrics (signups, purchases, MRR)

---

## 🎯 PLAN DE LANCEMENT (7 JOURS)

### Jour 1-2 : Infrastructure
- [ ] Créer namespace `konqer` dans K8s
- [ ] Setup database `konqer_production` (Postgres platform)
- [ ] Migrer schema SQL complet
- [ ] Configurer DO Secrets (OPENAI, STRIPE, APOLLO, LINKEDIN)
- [ ] Setup Keycloak realm + clients

### Jour 3-4 : Backend
- [ ] Coder API FastAPI (routers complets)
- [ ] Implémenter logique métier 12 services (GPT-4o + APIs)
- [ ] Stripe integration (checkout + webhooks)
- [ ] Tests unitaires endpoints critiques
- [ ] Build + push image (Kaniko)

### Jour 5-6 : Frontend
- [ ] Template landing page Next.js (dynamic config)
- [ ] Script copie vers 12 apps
- [ ] Dashboard utilisateur (konqer.app/dashboard)
- [ ] GitHub Actions CI/CD
- [ ] Deploy Kinsta (12 repos)

### Jour 7 : Production
- [ ] Deploy API K8s (saas node-pool)
- [ ] Deploy Admin backend (port-forward)
- [ ] Configure Kong routes + ingress
- [ ] DNS CNAME (12 sous-domaines)
- [ ] Tests end-to-end complets
- [ ] Monitoring dashboards

---

## ✅ CHECKLIST PRÉ-LANCEMENT

### Technique
- [ ] Database migrations appliquées
- [ ] Secrets configurés (DO Secrets)
- [ ] Keycloak realm + clients créés
- [ ] Kong routes configurées
- [ ] SSL certificats actifs (Let's Encrypt)
- [ ] Health checks passing (API /health)
- [ ] Monitoring dashboards configurés

### Business
- [ ] Stripe products créés (Founding 699€/an, Singles 99€/mois)
- [ ] Webhooks Stripe configurés + testés
- [ ] Email templates (welcome, unlock notification)
- [ ] Landing pages 12 services (copy + design)
- [ ] Dashboard utilisateur fonctionnel
- [ ] Admin backend accessible (port-forward)

### Marketing
- [ ] DNS configuré (konqer.app + 12 sous-domaines)
- [ ] Pages indexées Google (sitemap)
- [ ] Analytics setup (PostHog/Matomo)
- [ ] Warm-up social (Reddit, LinkedIn)
- [ ] Launch posts rédigés

---

## 📚 RESSOURCES COMPLÉMENTAIRES

### Documentation Interne
- `/docs/API.md` - Référence API complète
- `/docs/DEPLOYMENT.md` - Guide déploiement détaillé
- `/k8s/` - Manifests Kubernetes

### Infrastructure Existante
- Cluster BlueOcean K8s (DigitalOcean)
- Node-pool platform (Postgres, Redis, Kong, Keycloak)
- Node-pool saas (Apps deployment)
- Kaniko builds in-cluster
- DO Secrets Manager

### Services Externes
- Stripe (paiements)
- OpenAI API (génération)
- Apollo.io API (enrichment)
- LinkedIn API (social data)
- Resend/SendGrid (emails)
- Kinsta (frontend CDN)

---

**Prochaine étape :** Génération code API FastAPI complet + manifests K8s
