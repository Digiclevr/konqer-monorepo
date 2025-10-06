# Konqer Monorepo - Déploiement Multi-Domaines

## Architecture

### Environnement Local

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

### Environnement Production

| Service | App | URL |
|---------|-----|-----|
| Site principal | apps/web | https://konqer.app |
| Cold DM Personalizer | apps/cold-dm | https://cold-dm-personalizer.konqer.app |
| Outbound Battlecards AI | apps/battlecards | https://outbound-battlecards-ai.konqer.app |
| Sales Objection Crusher | apps/objection | https://sales-objection-crusher.konqer.app |
| API Backend | apps/api | https://api.konqer.app |

## Configuration DNS

Pour chaque sous-domaine, créer un enregistrement CNAME ou A pointant vers le serveur:

```
konqer.app                          A    <IP_SERVER>
cold-dm-personalizer.konqer.app     CNAME konqer.app
outbound-battlecards-ai.konqer.app  CNAME konqer.app
sales-objection-crusher.konqer.app  CNAME konqer.app
api.konqer.app                      CNAME konqer.app
```

## Déploiement

### Développement Local

```bash
# Installer les dépendances
pnpm install

# Démarrer tous les services en parallèle
pnpm dev
```

### Production

Chaque app peut être déployée indépendamment:

```bash
# Build d'une app spécifique
pnpm --filter=konqer-app build
pnpm --filter=cold-dm build
pnpm --filter=battlecards build
pnpm --filter=objection build
pnpm --filter=api build

# Start en production
pnpm --filter=konqer-app start
pnpm --filter=cold-dm start
pnpm --filter=battlecards start
pnpm --filter=objection start
pnpm --filter=api start
```

### Configuration Nginx (exemple)

```nginx
# Site principal
server {
    server_name konqer.app;
    location / {
        proxy_pass http://localhost:3000;
    }
}

# Cold DM Personalizer
server {
    server_name cold-dm-personalizer.konqer.app;
    location / {
        proxy_pass http://localhost:3001;
    }
}

# Outbound Battlecards AI
server {
    server_name outbound-battlecards-ai.konqer.app;
    location / {
        proxy_pass http://localhost:3002;
    }
}

# Sales Objection Crusher
server {
    server_name sales-objection-crusher.konqer.app;
    location / {
        proxy_pass http://localhost:3003;
    }
}

# API
server {
    server_name api.konqer.app;
    location / {
        proxy_pass http://localhost:4000;
    }
}
```

## Services Restants

Les 9 autres services peuvent être ajoutés en suivant le même pattern:

1. Copier une app existante: `cp -r apps/cold-dm apps/nouveau-service`
2. Modifier `package.json` (name + port)
3. Modifier `app/page.tsx` (contenu du service)
4. Ajouter à la configuration DNS/Nginx

### Ports disponibles

- 3004: Community Finder Pro
- 3005: LinkedIn Carousel Forge
- 3006: AI Cold Email Writer
- 3007: Startup Pitch Deck Builder
- 3008: AI Whitepaper Generator
- 3009: VC Deck Heatmap
- 3010: Webinar Demand Scanner
- 3011: Email WarmRanker
- 3012: Calendar No-Show Shield
