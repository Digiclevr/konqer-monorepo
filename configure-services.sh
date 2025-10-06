#!/bin/bash

# Configuration des services restants
# Service 4: Community Finder Pro (port 3004)
cat > apps/community-finder/package.json << 'EOF'
{
  "name": "community-finder",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3004",
    "build": "next build",
    "start": "next start -p 3004",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 5: LinkedIn Carousel Forge (port 3005)
cat > apps/carousel-forge/package.json << 'EOF'
{
  "name": "carousel-forge",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3005",
    "build": "next build",
    "start": "next start -p 3005",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 6: AI Cold Email Writer (port 3006)
cat > apps/cold-email/package.json << 'EOF'
{
  "name": "cold-email",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3006",
    "build": "next build",
    "start": "next start -p 3006",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 7: Startup Pitch Deck Builder (port 3007)
cat > apps/pitch-deck/package.json << 'EOF'
{
  "name": "pitch-deck",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3007",
    "build": "next build",
    "start": "next start -p 3007",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 8: AI Whitepaper Generator (port 3008)
cat > apps/whitepaper/package.json << 'EOF'
{
  "name": "whitepaper",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3008",
    "build": "next build",
    "start": "next start -p 3008",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 9: VC Deck Heatmap (port 3009)
cat > apps/deck-heatmap/package.json << 'EOF'
{
  "name": "deck-heatmap",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3009",
    "build": "next build",
    "start": "next start -p 3009",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 10: Webinar Demand Scanner (port 3010)
cat > apps/webinar-scanner/package.json << 'EOF'
{
  "name": "webinar-scanner",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3010",
    "build": "next build",
    "start": "next start -p 3010",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 11: Email WarmRanker (port 3011)
cat > apps/warmranker/package.json << 'EOF'
{
  "name": "warmranker",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3011",
    "build": "next build",
    "start": "next start -p 3011",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

# Service 12: Calendar No-Show Shield (port 3012)
cat > apps/no-show-shield/package.json << 'EOF'
{
  "name": "no-show-shield",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3012",
    "build": "next build",
    "start": "next start -p 3012",
    "lint": "next lint"
  },
  "dependencies": {
    "@konqer/ui": "workspace:*",
    "@konqer/utils": "workspace:*",
    "next": "14.2.4",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/react": "19.2.0",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.4",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5"
  }
}
EOF

echo "✅ Package.json files configured for all 9 services"
