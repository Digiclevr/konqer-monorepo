# Konqer Monorepo - Documentation

## Vue d'ensemble

Konqer est une plateforme SaaS multi-services organisée en monorepo. Le projet comprend un site principal et 12 applications de services spécialisés, tous partageant une API backend commune.

## Architecture

### Technologies

- **Framework**: Next.js 14.2.4 (App Router)
- **Package Manager**: pnpm
- **Build Tool**: Turbo
- **Runtime**: Node.js 20+
- **API Backend**: Fastify

### Structure du Projet

```
konqer-monorepo/
├── apps/
│   ├── web/              # Site principal (konqer.app)
│   ├── api/              # API Backend Fastify
│   ├── cold-dm/          # Cold DM Personalizer
│   ├── battlecards/      # Outbound Battlecards AI
│   ├── objection/        # Sales Objection Crusher
│   ├── community-finder/ # Community Finder Pro
│   ├── carousel-forge/   # LinkedIn Carousel Forge
│   ├── cold-email/       # AI Cold Email Writer
│   ├── pitch-deck/       # Startup Pitch Deck Builder
│   ├── whitepaper/       # AI Whitepaper Generator
│   ├── deck-heatmap/     # VC Deck Heatmap
│   ├── webinar-scanner/  # Webinar Demand Scanner
│   ├── warmranker/       # Email WarmRanker
│   └── no-show-shield/   # Calendar No-Show Shield
├── packages/
│   ├── ui/               # Composants UI partagés
│   ├── utils/            # Utilitaires partagés
│   └── config/           # Configuration partagée
├── docs/                 # Documentation
└── DEPLOYMENT.md         # Guide de déploiement
```

## Environnement Local

### Ports Locaux

| Service | App | Port | URL |
|---------|-----|------|-----|
| Site principal | apps/web | 3100 | http://localhost:3100 |
| Cold DM Personalizer | apps/cold-dm | 3101 | http://localhost:3101 |
| Outbound Battlecards AI | apps/battlecards | 3102 | http://localhost:3102 |
| Sales Objection Crusher | apps/objection | 3103 | http://localhost:3103 |
| Community Finder Pro | apps/community-finder | 3104 | http://localhost:3104 |
| LinkedIn Carousel Forge | apps/carousel-forge | 3105 | http://localhost:3105 |
| AI Cold Email Writer | apps/cold-email | 3106 | http://localhost:3106 |
| Startup Pitch Deck Builder | apps/pitch-deck | 3107 | http://localhost:3107 |
| AI Whitepaper Generator | apps/whitepaper | 3108 | http://localhost:3108 |
| VC Deck Heatmap | apps/deck-heatmap | 3109 | http://localhost:3109 |
| Webinar Demand Scanner | apps/webinar-scanner | 3110 | http://localhost:3110 |
| Email WarmRanker | apps/warmranker | 3111 | http://localhost:3111 |
| Calendar No-Show Shield | apps/no-show-shield | 3112 | http://localhost:3112 |
| API Backend | apps/api | 4000 | http://localhost:4000 |

### Installation et Démarrage

```bash
# Installer pnpm globalement
npm install -g pnpm

# Installer les dépendances
pnpm install

# Démarrer tous les services en parallèle
pnpm dev
```

### Commandes Disponibles

```bash
# Développement
pnpm dev           # Démarre tous les services en mode développement

# Build
pnpm build         # Build toutes les applications

# Linting
pnpm lint          # Vérifie le code avec ESLint

# Build spécifique
pnpm --filter=konqer-app build
pnpm --filter=cold-dm build

# Dev spécifique
pnpm --filter=api dev
```

## Configuration

### Turbo (turbo.json)

Le projet utilise Turbo pour la gestion des tâches en parallèle :

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"]
    },
    "dev": {
      "cache": false
    },
    "lint": {},
    "start": {}
  }
}
```

### Workspace (pnpm-workspace.yaml)

```yaml
packages:
  - apps/*
  - packages/*
```

### Next.js Configuration

Chaque application Next.js utilise une configuration similaire :

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {}
};

export default nextConfig;
```

### TypeScript

Configuration TypeScript partagée dans `tsconfig.json` à la racine du projet.

## Services

### Site Principal (konqer-app)

Le site principal hébergé sur konqer.app présente tous les services disponibles et sert de point d'entrée à l'écosystème Konqer.

### Services Spécialisés

Chaque service est une application Next.js indépendante avec :
- Sa propre page d'accueil
- Un lien de retour vers le site principal
- Sa propre documentation API
- Son propre port de développement

### API Backend

L'API Fastify fournit les fonctionnalités backend partagées pour tous les services.

## Environnement Production

### URLs Production

| Service | URL |
|---------|-----|
| Site principal | https://konqer.app |
| Cold DM Personalizer | https://cold-dm-personalizer.konqer.app |
| Outbound Battlecards AI | https://outbound-battlecards-ai.konqer.app |
| Sales Objection Crusher | https://sales-objection-crusher.konqer.app |
| API Backend | https://api.konqer.app |

### Configuration DNS

Pour chaque sous-domaine :

```
konqer.app                          A    <IP_SERVER>
cold-dm-personalizer.konqer.app     CNAME konqer.app
outbound-battlecards-ai.konqer.app  CNAME konqer.app
sales-objection-crusher.konqer.app  CNAME konqer.app
api.konqer.app                      CNAME konqer.app
```

### Déploiement

Voir [DEPLOYMENT.md](../DEPLOYMENT.md) pour les détails complets du déploiement.

## Packages Partagés

### @konqer/ui

Composants UI réutilisables (Button, etc.)

### @konqer/utils

Utilitaires et constantes partagés, incluant la liste des 12 services.

### @konqer/config

Configuration partagée pour tous les projets.

## Développement

### Ajouter un Nouveau Service

1. Copier une app existante :
   ```bash
   cp -r apps/cold-dm apps/nouveau-service
   ```

2. Modifier `package.json` :
   ```json
   {
     "name": "nouveau-service",
     "scripts": {
       "dev": "next dev -p 31XX",
       "start": "next start -p 31XX"
     }
   }
   ```

3. Modifier le contenu dans `app/page.tsx`

4. Ajouter à la configuration DNS/Nginx en production

### Résolution de Problèmes

#### Port déjà utilisé

Si un port est déjà utilisé :

```bash
# Vérifier les ports
lsof -i :3100-3112

# Tuer un processus
kill -9 <PID>
```

#### Erreur de build

Si le build échoue :

```bash
# Nettoyer et réinstaller
rm -rf node_modules
pnpm install

# Build avec logs détaillés
pnpm build --verbose
```

## Ressources

- [Documentation Next.js](https://nextjs.org/docs)
- [Documentation Turbo](https://turbo.build/repo/docs)
- [Documentation pnpm](https://pnpm.io)
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Guide de déploiement complet
