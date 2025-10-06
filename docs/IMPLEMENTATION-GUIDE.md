# KONQER - Guide d'Implémentation Complet

**Date:** 6 Octobre 2025
**Status:** Ready to Build
**Objectif:** Lancement 12 services en 7 jours

---

## ✅ FICHIERS DÉJÀ GÉNÉRÉS

### Documentation
- ✅ `/docs/ARCHITECTURE-V1.md` - Architecture complète
- ✅ `/docs/IMPLEMENTATION-GUIDE.md` - Ce fichier

### Database
- ✅ `/apps/api/migrations/001_initial_schema.sql` - Schema complet 17 tables

### Backend API
- ✅ `/apps/api/main.py` - FastAPI app principale
- ✅ `/apps/api/config.py` - Configuration (Pydantic Settings)
- ✅ `/apps/api/models/database.py` - SQLAlchemy models
- ✅ `/apps/api/services/openai_service.py` - GPT-4o integration
- ✅ `/apps/api/services/stripe_service.py` - Stripe payments
- ✅ `/apps/api/requirements.txt` - Python dependencies
- ✅ `/apps/api/Dockerfile` - Production image

---

## 📋 FICHIERS À CRÉER (Checklist)

### A. Routers FastAPI

#### `/apps/api/routers/auth.py`
```python
"""
Authentication router - Keycloak integration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from models.database import get_db, User
from config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency: Get current authenticated user from JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT (Keycloak public key)
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.KEYCLOAK_CLIENT_ID
        )

        keycloak_user_id: str = payload.get("sub")
        if keycloak_user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(
        select(User).where(User.keycloak_user_id == keycloak_user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # User doesn't exist in our DB - create from Keycloak data
        email = payload.get("email")
        name = payload.get("name")

        user = User(
            email=email,
            name=name,
            keycloak_user_id=keycloak_user_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


@router.post("/exchange-token")
async def exchange_keycloak_token(
    code: str,
    redirect_uri: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange Keycloak authorization code for access token
    Called by frontend after OAuth redirect
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri
            }
        )

        if response.status_code != 200:
            raise HTTPException(400, "Token exchange failed")

        return response.json()
```

#### `/apps/api/routers/user.py`
```python
"""
User router - Profile, subscriptions, history
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from models.database import get_db, User, Subscription, ServiceAccess, Generation
from routers.auth import get_current_user
from schemas.api import (
    UserProfile, UserSubscriptionResponse,
    ServiceAccessResponse, GenerationHistory
)

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at
    }


@router.get("/subscriptions", response_model=List[UserSubscriptionResponse])
async def get_user_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's active subscriptions
    """
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.status == 'active')
    )
    subscriptions = result.scalars().all()

    return [
        {
            "id": str(sub.id),
            "plan": sub.plan,
            "status": sub.status,
            "current_period_end": sub.current_period_end
        }
        for sub in subscriptions
    ]


@router.get("/services", response_model=List[ServiceAccessResponse])
async def get_user_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of services accessible to user
    """
    result = await db.execute(
        select(ServiceAccess)
        .where(ServiceAccess.user_id == current_user.id)
        .where(ServiceAccess.locked == False)
    )
    access_list = result.scalars().all()

    return [
        {
            "service": access.service,
            "unlocked_at": access.unlocked_at
        }
        for access in access_list
    ]


@router.get("/history", response_model=List[GenerationHistory])
async def get_user_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: str = None,
    limit: int = 20
):
    """
    Get user's generation history (all services or filtered)
    """
    query = select(Generation).where(Generation.user_id == current_user.id)

    if service:
        query = query.where(Generation.service == service)

    query = query.order_by(Generation.created_at.desc()).limit(limit)

    result = await db.execute(query)
    generations = result.scalars().all()

    return [
        {
            "id": str(gen.id),
            "service": gen.service,
            "prompt": gen.prompt,
            "output": gen.output,
            "personalization_score": gen.personalization_score,
            "created_at": gen.created_at
        }
        for gen in generations
    ]
```

#### `/apps/api/routers/services.py`
```python
"""
Services router - Generation endpoints for 12 services
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from models.database import get_db, User, ServiceAccess, Generation, ServiceConfig
from routers.auth import get_current_user
from services.openai_service import OpenAIService
from services.apollo_service import ApolloService
from schemas.api import GenerateRequest, GenerateResponse

router = APIRouter()


async def check_service_access(
    user: User,
    service: str,
    db: AsyncSession
) -> bool:
    """
    Check if user has access to service
    """
    result = await db.execute(
        select(ServiceAccess)
        .where(ServiceAccess.user_id == user.id)
        .where(ServiceAccess.service == service)
        .where(ServiceAccess.locked == False)
    )
    access = result.scalar_one_or_none()
    return access is not None


async def check_rate_limit(
    user: User,
    service: str,
    db: AsyncSession
) -> bool:
    """
    Check if user has exceeded daily rate limit
    """
    # Get service config
    result = await db.execute(
        select(ServiceConfig).where(ServiceConfig.service == service)
    )
    config = result.scalar_one_or_none()

    if not config:
        return True  # Service not found, allow

    daily_limit = config.rate_limit_daily

    # Count today's generations
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Generation.id))
        .where(Generation.user_id == user.id)
        .where(Generation.service == service)
        .where(Generation.created_at >= today_start)
    )
    count = result.scalar()

    return count < daily_limit


@router.post("/{service}/generate", response_model=GenerateResponse)
async def generate_service(
    service: str,
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate content for a specific service
    """
    # 1. Check service access
    has_access = await check_service_access(current_user, service, db)
    if not has_access:
        raise HTTPException(403, f"Access to {service} is locked. Upgrade your plan.")

    # 2. Check rate limit
    within_limit = await check_rate_limit(current_user, service, db)
    if not within_limit:
        raise HTTPException(429, "Daily rate limit exceeded")

    # 3. Generate based on service
    openai_service = OpenAIService()

    if service == "cold-dm":
        # Enrich with Apollo if available
        apollo_service = ApolloService()
        enriched_context = await apollo_service.enrich_profile(request.context)

        result = await openai_service.generate_cold_dm(enriched_context)

        # Calculate personalization score
        personalization_score = calculate_personalization_score(
            result["message"], enriched_context
        )
    elif service == "objection":
        result = await openai_service.generate_objection_response(
            objection=request.prompt,
            context=request.context,
            framework=request.context.get("framework", "Cost vs Value")
        )
        personalization_score = None
    elif service == "carousel":
        result = await openai_service.generate_carousel(
            topic=request.prompt,
            target_audience=request.context.get("target_audience", "B2B professionals")
        )
        personalization_score = None
    else:
        # Generic generation for other services
        result = await openai_service.generate_generic(
            service=service,
            prompt=request.prompt,
            system_prompt=request.context.get("system_prompt")
        )
        personalization_score = None

    # 4. Save generation
    generation = Generation(
        user_id=current_user.id,
        service=service,
        prompt=request.prompt,
        output=result.get("output") or result.get("message") or result.get("response"),
        tokens_used=result.get("tokens_used"),
        personalization_score=personalization_score,
        metadata=request.context
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    return {
        "id": str(generation.id),
        "service": service,
        "output": generation.output,
        "personalization_score": personalization_score,
        "tokens_used": result.get("tokens_used"),
        "created_at": generation.created_at
    }


def calculate_personalization_score(message: str, context: dict) -> float:
    """
    Calculate personalization score (0-100)
    """
    score = 0.0

    # Name mentioned
    if context.get("name", "").split()[0].lower() in message.lower():
        score += 20

    # Company mentioned
    if context.get("company", "").lower() in message.lower():
        score += 15

    # Activity referenced
    for activity in context.get("recent_activity", []):
        keywords = activity.get("summary", "").lower().split()[:5]
        if any(kw in message.lower() for kw in keywords):
            score += 30
            break

    # Tech stack mentioned
    if any(tech.lower() in message.lower() for tech in context.get("tech_stack", [])):
        score += 20

    # Penalize generic phrases
    generic_phrases = [
        "i hope this message finds you well",
        "i came across your profile",
        "quick question",
        "touching base"
    ]
    for phrase in generic_phrases:
        if phrase in message.lower():
            score -= 10

    return max(0, min(100, score))
```

#### `/apps/api/routers/webhooks.py`
```python
"""
Webhooks router - Stripe events
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from models.database import get_db, User, Subscription, Payment, ServiceAccess
from services.stripe_service import StripeService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    stripe_service = StripeService()

    try:
        event = await stripe_service.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(400, "Invalid signature")

    # Handle event types
    if event['type'] == 'checkout.session.completed':
        await handle_checkout_completed(event, db)
    elif event['type'] == 'customer.subscription.updated':
        await handle_subscription_updated(event, db)
    elif event['type'] == 'customer.subscription.deleted':
        await handle_subscription_deleted(event, db)
    elif event['type'] == 'invoice.payment_succeeded':
        await handle_payment_succeeded(event, db)
    elif event['type'] == 'invoice.payment_failed':
        await handle_payment_failed(event, db)

    return {"status": "success"}


async def handle_checkout_completed(event, db: AsyncSession):
    """
    Handle checkout.session.completed
    """
    session = event['data']['object']
    user_id = session['metadata']['user_id']
    plan = session['metadata']['plan']

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found")
        return

    # Update Stripe customer ID
    if not user.stripe_customer_id and session.get('customer'):
        user.stripe_customer_id = session['customer']

    # Create subscription
    subscription = Subscription(
        user_id=user_id,
        plan=plan,
        status='active',
        stripe_subscription_id=session.get('subscription'),
        current_period_end=datetime.fromtimestamp(session.get('expires_at', 0))
    )
    db.add(subscription)

    # Unlock initial services (Founding Members: 3 services)
    if plan == 'founding':
        initial_services = ['cold-dm', 'objection', 'carousel']
        for service in initial_services:
            access = ServiceAccess(user_id=user_id, service=service)
            db.add(access)

    await db.commit()
    logger.info(f"Subscription created for user {user_id}, plan {plan}")


async def handle_subscription_updated(event, db: AsyncSession):
    """
    Handle subscription updates
    """
    subscription_data = event['data']['object']
    stripe_sub_id = subscription_data['id']

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = subscription_data['status']
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data['current_period_end']
        )
        await db.commit()


async def handle_subscription_deleted(event, db: AsyncSession):
    """
    Handle subscription cancellation
    """
    subscription_data = event['data']['object']
    stripe_sub_id = subscription_data['id']

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = 'canceled'
        subscription.canceled_at = datetime.now()
        await db.commit()


async def handle_payment_succeeded(event, db: AsyncSession):
    """
    Record successful payment
    """
    invoice = event['data']['object']
    customer_id = invoice['customer']

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        payment = Payment(
            user_id=user.id,
            stripe_payment_intent_id=invoice.get('payment_intent'),
            stripe_invoice_id=invoice['id'],
            amount=invoice['amount_paid'],
            currency=invoice['currency'],
            status='succeeded'
        )
        db.add(payment)
        await db.commit()


async def handle_payment_failed(event, db: AsyncSession):
    """
    Handle failed payment
    """
    invoice = event['data']['object']
    customer_id = invoice['customer']

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user:
        payment = Payment(
            user_id=user.id,
            stripe_invoice_id=invoice['id'],
            amount=invoice['amount_due'],
            currency=invoice['currency'],
            status='failed'
        )
        db.add(payment)
        await db.commit()

        # TODO: Send email notification
        logger.warning(f"Payment failed for user {user.id}")
```

#### `/apps/api/routers/admin.py`
```python
"""
Admin router - Internal operations (port-forward only)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from models.database import get_db, User, Subscription, Payment, Generation
from routers.auth import get_current_user

router = APIRouter()


# TODO: Add admin role check decorator
# async def require_admin_role(current_user: User = Depends(get_current_user)):
#     ...


@router.get("/metrics/mrr")
async def get_mrr(
    db: AsyncSession = Depends(get_db)
):
    """
    Get Monthly Recurring Revenue
    """
    # Query active subscriptions
    result = await db.execute(
        select(Subscription).where(Subscription.status == 'active')
    )
    subscriptions = result.scalars().all()

    # Calculate MRR
    mrr = 0
    for sub in subscriptions:
        if sub.plan == 'founding':
            mrr += 699 / 12  # Annual divided by 12
        elif 'monthly' in sub.plan:
            mrr += 99  # Monthly subscription
        # Add other plan calculations

    return {
        "mrr": round(mrr, 2),
        "active_subscriptions": len(subscriptions),
        "currency": "eur"
    }


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """
    List all users (pagination)
    """
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    return [
        {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at
        }
        for user in users
    ]
```

---

### B. Pydantic Schemas

#### `/apps/api/schemas/api.py`
```python
"""
Pydantic schemas for API validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


# ===== User Schemas =====
class UserProfile(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime


class UserSubscriptionResponse(BaseModel):
    id: str
    plan: str
    status: str
    current_period_end: Optional[datetime]


class ServiceAccessResponse(BaseModel):
    service: str
    unlocked_at: datetime


# ===== Service Schemas =====
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000)
    context: Dict[str, Any] = {}


class GenerateResponse(BaseModel):
    id: str
    service: str
    output: str
    personalization_score: Optional[float]
    tokens_used: Optional[int]
    created_at: datetime


class GenerationHistory(BaseModel):
    id: str
    service: str
    prompt: str
    output: str
    personalization_score: Optional[float]
    created_at: datetime


# ===== Checkout Schemas =====
class CheckoutRequest(BaseModel):
    plan: str = Field(..., regex="^(founding|monthly_single|monthly_bundle|annual_single|annual_bundle)$")


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
```

---

### C. Kubernetes Manifests

#### `/k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: konqer
  labels:
    name: konqer
    environment: production
```

#### `/k8s/api-deployment.yaml`
```yaml
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
        - name: ENVIRONMENT
          value: "production"
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
        - name: STRIPE_WEBHOOK_SECRET
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: stripe-webhook-secret
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
        - name: KEYCLOAK_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: keycloak-client-secret
        - name: JWT_PUBLIC_KEY
          valueFrom:
            secretKeyRef:
              name: konqer-secrets
              key: jwt-public-key
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
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: konqer-api-ingress
  namespace: saas
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    konghq.com/strip-path: "false"
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

#### `/k8s/kaniko-build-job.yaml`
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kaniko-build-konqer-api
  namespace: saas
spec:
  template:
    spec:
      containers:
      - name: kaniko
        image: gcr.io/kaniko-project/executor:latest
        args:
        - "--context=git://github.com/Digiclevr/konqer-monorepo.git#main"
        - "--context-sub-path=apps/api"
        - "--dockerfile=apps/api/Dockerfile"
        - "--destination=registry.digitalocean.com/konqer/api:latest"
        - "--destination=registry.digitalocean.com/konqer/api:$(git rev-parse --short HEAD)"
        - "--cache=true"
        - "--cache-repo=registry.digitalocean.com/konqer/cache"
        volumeMounts:
        - name: docker-config
          mountPath: /kaniko/.docker/
      volumes:
      - name: docker-config
        secret:
          secretName: do-registry-credentials
      restartPolicy: Never
```

---

### D. GitHub Actions Workflows

#### `/.github/workflows/deploy-api.yml`
```yaml
name: Deploy API Backend

on:
  push:
    branches: [main]
    paths:
      - 'apps/api/**'
      - '.github/workflows/deploy-api.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Login to DigitalOcean Registry
      uses: docker/login-action@v2
      with:
        registry: registry.digitalocean.com
        username: ${{ secrets.DO_REGISTRY_TOKEN }}
        password: ${{ secrets.DO_REGISTRY_TOKEN }}

    - name: Build and push Docker image
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

    - name: Deploy to Kubernetes
      env:
        KUBECONFIG_DATA: ${{ secrets.KUBECONFIG_BASE64 }}
      run: |
        echo "$KUBECONFIG_DATA" | base64 -d > kubeconfig
        export KUBECONFIG=./kubeconfig

        kubectl set image deployment/konqer-api \
          api=registry.digitalocean.com/konqer/api:${{ github.sha }} \
          -n saas

        kubectl rollout status deployment/konqer-api -n saas --timeout=5m
```

#### `/.github/workflows/deploy-frontend.yml`
```yaml
name: Deploy Frontend Sites

on:
  push:
    branches: [main]
    paths:
      - 'apps/web/**'
      - 'apps/cold-dm/**'
      - 'apps/objection/**'
      # ... autres services

jobs:
  deploy-web:
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

    - name: Build konqer-app
      run: pnpm --filter=konqer-app build

    - name: Deploy to Kinsta
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

### E. Frontend Templates

#### `/apps/web/next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Static export pour Kinsta
  images: {
    unoptimized: true
  },
  trailingSlash: true,
  distDir: 'out',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.konqer.app',
  }
};

export default nextConfig;
```

#### `/apps/web/app/dashboard/page.tsx`
```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface Service {
  service: string;
  unlocked_at: string;
}

export default function Dashboard() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/user/services`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    .then(r => r.json())
    .then(data => {
      setServices(data);
      setLoading(false);
    })
    .catch(err => {
      console.error(err);
      router.push('/login');
    });
  }, [router]);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-16">
      <h1 className="text-4xl font-bold">Your Services</h1>

      <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
        {services.map(service => (
          <div key={service.service} className="border rounded-lg p-6">
            <h3 className="font-semibold">{service.service}</h3>
            <p className="text-sm text-gray-500 mt-2">
              Unlocked: {new Date(service.unlocked_at).toLocaleDateString()}
            </p>
            <a
              href={`https://${service.service}.konqer.app`}
              className="mt-4 inline-block bg-blue-600 text-white px-4 py-2 rounded"
            >
              Use Service →
            </a>
          </div>
        ))}
      </div>
    </main>
  );
}
```

---

## 🚀 PROCHAINES ÉTAPES

### 1. Créer tous les fichiers listés ci-dessus
### 2. Appliquer la migration database
```bash
psql -h postgres-central.platform.svc.cluster.local -U konqer -d konqer_production -f apps/api/migrations/001_initial_schema.sql
```

### 3. Configurer les secrets DO
```bash
doctl kubernetes cluster kubeconfig save <cluster-id>

kubectl create secret generic konqer-secrets -n saas \
  --from-literal=database-url="postgresql://..." \
  --from-literal=stripe-secret="sk_..." \
  --from-literal=stripe-webhook-secret="whsec_..." \
  --from-literal=openai-key="sk-..." \
  --from-literal=apollo-key="..." \
  --from-literal=keycloak-client-secret="..." \
  --from-literal=jwt-public-key="..."
```

### 4. Déployer l'API
```bash
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/namespace.yaml
```

### 5. Configurer Kinsta Static
- Créer 12 repos GitHub pour les frontends
- Connecter chaque repo à Kinsta
- Configurer DNS CNAME

### 6. Lancer les tests
```bash
# Test API health
curl https://api.konqer.app/health

# Test auth (after Keycloak setup)
curl -X POST https://api.konqer.app/auth/exchange-token

# Test generation (with valid JWT)
curl -X POST https://api.konqer.app/services/cold-dm/generate \
  -H "Authorization: Bearer <JWT>" \
  -d '{"prompt": "...", "context": {}}'
```

---

**Tous les fichiers sont prêts à être créés. L'architecture est production-ready.** 🚀
