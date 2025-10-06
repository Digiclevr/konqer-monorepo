-- ============================================
-- KONQER DATABASE SCHEMA V1
-- ============================================
-- Database: konqer_production
-- Postgres: 15+
-- Date: 2025-10-06

-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Full-text search

-- ============================================
-- CUSTOM TYPES
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

CREATE TYPE payment_status AS ENUM (
  'succeeded',
  'failed',
  'refunded',
  'pending'
);

CREATE TYPE admin_role AS ENUM (
  'superadmin',
  'support',
  'finance',
  'developer'
);

-- ============================================
-- USERS & AUTH
-- ============================================
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  stripe_customer_id VARCHAR UNIQUE,
  keycloak_user_id VARCHAR UNIQUE,
  avatar_url TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);
CREATE INDEX idx_users_keycloak ON users(keycloak_user_id);
CREATE INDEX idx_users_created ON users(created_at DESC);

-- Trigger auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SUBSCRIPTIONS & PAYMENTS
-- ============================================
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  plan subscription_plan NOT NULL,
  status subscription_status NOT NULL DEFAULT 'active',
  stripe_subscription_id VARCHAR UNIQUE,
  stripe_price_id VARCHAR,
  current_period_start TIMESTAMP,
  current_period_end TIMESTAMP,
  cancel_at_period_end BOOLEAN DEFAULT false,
  canceled_at TIMESTAMP,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);
CREATE INDEX idx_subscriptions_created ON subscriptions(created_at DESC);

CREATE TRIGGER update_subscriptions_updated_at
  BEFORE UPDATE ON subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Service access (Founding Members rolling unlock)
CREATE TABLE service_access (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  service VARCHAR(100) NOT NULL,
  unlocked_at TIMESTAMP DEFAULT NOW(),
  locked BOOLEAN DEFAULT false,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, service)
);

CREATE INDEX idx_service_access_user ON service_access(user_id);
CREATE INDEX idx_service_access_service ON service_access(service);
CREATE INDEX idx_service_access_unlocked ON service_access(user_id, service) WHERE locked = false;

-- Payments history
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
  stripe_payment_intent_id VARCHAR UNIQUE,
  stripe_invoice_id VARCHAR,
  amount INTEGER NOT NULL,  -- Centimes (69900 = 699€)
  currency VARCHAR(3) DEFAULT 'eur',
  status payment_status NOT NULL,
  payment_method VARCHAR(50),  -- 'card', 'paypal', etc.
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created ON payments(created_at DESC);
CREATE INDEX idx_payments_stripe_intent ON payments(stripe_payment_intent_id);

-- ============================================
-- SERVICES GENERATIONS
-- ============================================
CREATE TABLE generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  service VARCHAR(100) NOT NULL,
  prompt TEXT,
  output TEXT,
  tokens_used INTEGER,
  personalization_score FLOAT,  -- 0-100 for cold-dm, objection, etc.
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_generations_user ON generations(user_id);
CREATE INDEX idx_generations_user_service ON generations(user_id, service);
CREATE INDEX idx_generations_service ON generations(service);
CREATE INDEX idx_generations_created ON generations(created_at DESC);
CREATE INDEX idx_generations_user_created ON generations(user_id, created_at DESC);

-- Rate limiting tracking (alternative to Redis)
CREATE TABLE rate_limits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  service VARCHAR(100) NOT NULL,
  window_start TIMESTAMP NOT NULL,
  request_count INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, service, window_start)
);

CREATE INDEX idx_rate_limits_user_service ON rate_limits(user_id, service, window_start);

-- ============================================
-- SERVICE CONFIGS
-- ============================================
CREATE TABLE service_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  type VARCHAR(50),  -- 'Blue', 'Red', 'Core'
  description TEXT,
  pricing_monthly INTEGER,  -- Centimes
  pricing_annual INTEGER,
  rate_limit_daily INTEGER DEFAULT 100,
  rate_limit_monthly INTEGER DEFAULT 3000,
  enabled BOOLEAN DEFAULT true,
  config JSONB DEFAULT '{}'::jsonb,  -- Headline, CTA, colors, features, etc.
  updated_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_service_configs_service ON service_configs(service);
CREATE INDEX idx_service_configs_slug ON service_configs(slug);
CREATE INDEX idx_service_configs_enabled ON service_configs(enabled);

CREATE TRIGGER update_service_configs_updated_at
  BEFORE UPDATE ON service_configs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ADMIN & INTERNAL
-- ============================================
CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  role admin_role NOT NULL DEFAULT 'support',
  keycloak_user_id VARCHAR UNIQUE,
  last_login_at TIMESTAMP,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_admin_users_email ON admin_users(email);
CREATE INDEX idx_admin_users_role ON admin_users(role);

CREATE TRIGGER update_admin_users_updated_at
  BEFORE UPDATE ON admin_users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Feature flags (A/B testing, gradual rollouts)
CREATE TABLE feature_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  flag_key VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  enabled BOOLEAN DEFAULT false,
  rollout_percentage INTEGER DEFAULT 100,  -- 0-100%
  config JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feature_flags_key ON feature_flags(flag_key);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(enabled);

CREATE TRIGGER update_feature_flags_updated_at
  BEFORE UPDATE ON feature_flags
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Audit logs (admin actions)
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID REFERENCES admin_users(id) ON DELETE SET NULL,
  action VARCHAR(100) NOT NULL,  -- 'user.unlock_service', 'config.update', etc.
  entity_type VARCHAR(50),  -- 'user', 'service', 'subscription'
  entity_id UUID,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_admin ON audit_logs(admin_user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- ============================================
-- ANALYTICS & TRACKING
-- ============================================
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  event_type VARCHAR(100) NOT NULL,  -- 'page_view', 'generation', 'checkout', 'purchase'
  service VARCHAR(100),
  metadata JSONB DEFAULT '{}'::jsonb,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_user ON events(user_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_service ON events(service);
CREATE INDEX idx_events_created ON events(created_at DESC);
CREATE INDEX idx_events_type_created ON events(event_type, created_at DESC);
CREATE INDEX idx_events_user_created ON events(user_id, created_at DESC);

-- API keys (for programmatic access)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  key_hash VARCHAR(255) UNIQUE NOT NULL,  -- SHA256 hash
  key_prefix VARCHAR(20) NOT NULL,  -- First chars for display
  name VARCHAR(255),
  last_used_at TIMESTAMP,
  expires_at TIMESTAMP,
  revoked BOOLEAN DEFAULT false,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(user_id) WHERE revoked = false AND (expires_at IS NULL OR expires_at > NOW());

-- ============================================
-- EMAIL TEMPLATES & QUEUE
-- ============================================
CREATE TABLE email_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key VARCHAR(100) UNIQUE NOT NULL,  -- 'founding_welcome', 'service_unlocked'
  subject VARCHAR(255) NOT NULL,
  body_html TEXT NOT NULL,
  body_text TEXT,
  variables JSONB DEFAULT '[]'::jsonb,  -- ['{{user.name}}', '{{service.name}}']
  metadata JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_templates_key ON email_templates(template_key);

CREATE TRIGGER update_email_templates_updated_at
  BEFORE UPDATE ON email_templates
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE email_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  template_key VARCHAR(100) NOT NULL,
  to_email VARCHAR(255) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body_html TEXT NOT NULL,
  variables JSONB DEFAULT '{}'::jsonb,
  status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'sent', 'failed'
  sent_at TIMESTAMP,
  error_message TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_created ON email_queue(created_at);
CREATE INDEX idx_email_queue_user ON email_queue(user_id);

-- ============================================
-- SEED DATA - 12 SERVICES
-- ============================================
INSERT INTO service_configs (service, name, slug, type, description, pricing_monthly, pricing_annual, config) VALUES
  (
    'cold-dm',
    'Cold DM Personalizer',
    'cold-dm-personalizer',
    'Blue',
    'AI-powered cold LinkedIn DM generation with Apollo + LinkedIn enrichment',
    9900,
    99000,
    '{
      "headline": "Generate Hyper-Personalized Cold DMs in Seconds",
      "subheadline": "Powered by Apollo.io + LinkedIn + GPT-4o",
      "cta": "Start Personalizing",
      "features": [
        "Apollo.io contact enrichment",
        "LinkedIn activity analysis",
        "Personalization scoring (0-100)",
        "150-word optimized messages"
      ],
      "colors": {"primary": "#2563eb", "accent": "#3b82f6"}
    }'::jsonb
  ),
  (
    'battlecards',
    'Outbound Battlecards AI',
    'outbound-battlecards-ai',
    'Blue',
    'Competitive battlecards generator for sales teams',
    9900,
    99000,
    '{
      "headline": "Crush Competitors with AI-Generated Battlecards",
      "subheadline": "Know exactly what to say when prospects mention competitors",
      "cta": "Build Battlecards",
      "features": ["Competitor analysis", "Objection handling", "Feature comparisons", "Positioning statements"],
      "colors": {"primary": "#dc2626", "accent": "#ef4444"}
    }'::jsonb
  ),
  (
    'objection',
    'Sales Objection Crusher',
    'sales-objection-crusher',
    'Blue',
    'Generate proven objection handling responses using 50+ frameworks',
    9900,
    99000,
    '{
      "headline": "Turn Objections into Opportunities",
      "subheadline": "AI-powered responses using proven sales frameworks",
      "cta": "Crush Objections",
      "features": ["50+ objection patterns", "Framework-based responses", "Case study integration", "Empathy + Evidence + Action"],
      "colors": {"primary": "#16a34a", "accent": "#22c55e"}
    }'::jsonb
  ),
  (
    'community-finder',
    'Community Finder Pro',
    'community-finder-pro',
    'Blue',
    'Find high-intent communities where your ICP hangs out',
    9900,
    99000,
    '{
      "headline": "Find Where Your Buyers Actually Hang Out",
      "subheadline": "Reddit, Slack, Discord, LinkedIn Groups - all in one search",
      "cta": "Find Communities",
      "features": ["Multi-platform search", "Member count estimates", "Engagement scoring", "Best posting times"],
      "colors": {"primary": "#9333ea", "accent": "#a855f7"}
    }'::jsonb
  ),
  (
    'carousel',
    'LinkedIn Carousel Forge',
    'linkedin-carousel-forge',
    'Blue',
    '10-slide viral LinkedIn carousels with Canva export',
    9900,
    99000,
    '{
      "headline": "Create Viral LinkedIn Carousels in Minutes",
      "subheadline": "Research + Design + Export to Canva - All automated",
      "cta": "Forge Carousel",
      "features": ["10-slide structured content", "Web research integration", "DALL-E visual prompts", "Canva template export"],
      "colors": {"primary": "#0891b2", "accent": "#06b6d4"}
    }'::jsonb
  ),
  (
    'cold-email',
    'AI Cold Email Writer',
    'ai-cold-email-writer',
    'Red',
    'High-converting cold email sequences (3-7 emails)',
    9900,
    99000,
    '{
      "headline": "Cold Emails That Actually Get Replies",
      "subheadline": "Multi-step sequences optimized for B2B conversion",
      "cta": "Write Sequence",
      "features": ["3-7 email sequences", "A/B variant generation", "Personalization tokens", "Follow-up timing optimization"],
      "colors": {"primary": "#ea580c", "accent": "#f97316"}
    }'::jsonb
  ),
  (
    'pitch-deck',
    'Startup Pitch Deck Builder',
    'startup-pitch-deck-builder',
    'Core',
    'VC-ready pitch decks following Y Combinator template',
    9900,
    99000,
    '{
      "headline": "Build Your Pitch Deck Like YC-Backed Startups",
      "subheadline": "15-slide proven structure + market research included",
      "cta": "Build Deck",
      "features": ["YC template structure", "Market sizing (TAM/SAM/SOM)", "Competitor analysis", "Financial projections"],
      "colors": {"primary": "#7c3aed", "accent": "#8b5cf6"}
    }'::jsonb
  ),
  (
    'whitepaper',
    'AI Whitepaper Generator',
    'ai-whitepaper-generator',
    'Core',
    'Technical whitepapers for B2B lead generation',
    9900,
    99000,
    '{
      "headline": "Generate Technical Whitepapers in 30 Minutes",
      "subheadline": "Research + Writing + References - All automated",
      "cta": "Generate Whitepaper",
      "features": ["Academic research integration", "Citation management", "Executive summary", "10-25 page output"],
      "colors": {"primary": "#0f766e", "accent": "#14b8a6"}
    }'::jsonb
  ),
  (
    'deck-heatmap',
    'VC Deck Heatmap',
    'vc-deck-heatmap',
    'Blue',
    'Analyze your pitch deck like a VC (attention heatmap)',
    9900,
    99000,
    '{
      "headline": "See Your Deck Through VC Eyes",
      "subheadline": "AI-powered attention heatmap + slide scoring",
      "cta": "Analyze Deck",
      "features": ["Slide-by-slide scoring", "Attention heatmap", "VC feedback simulation", "Improvement suggestions"],
      "colors": {"primary": "#be123c", "accent": "#e11d48"}
    }'::jsonb
  ),
  (
    'webinar',
    'Webinar Demand Scanner',
    'webinar-demand-scanner',
    'Blue',
    'Find high-demand webinar topics in your niche',
    9900,
    99000,
    '{
      "headline": "Find Webinar Topics That Actually Fill Seats",
      "subheadline": "Search volume + competitor analysis + title suggestions",
      "cta": "Scan Demand",
      "features": ["Google Trends integration", "Competitor webinar analysis", "Title A/B variants", "Best days/times"],
      "colors": {"primary": "#0369a1", "accent": "#0284c7"}
    }'::jsonb
  ),
  (
    'warmranker',
    'Email WarmRanker',
    'email-warmranker',
    'Red',
    'Score your cold email warmth (avoid spam folder)',
    9900,
    99000,
    '{
      "headline": "Stop Landing in Spam. Score Your Email Warmth.",
      "subheadline": "AI analysis + deliverability recommendations",
      "cta": "Check Warmth",
      "features": ["Spam trigger detection", "Personalization scoring", "Domain reputation check", "Improvement tips"],
      "colors": {"primary": "#ca8a04", "accent": "#eab308"}
    }'::jsonb
  ),
  (
    'no-show-shield',
    'Calendar No-Show Shield',
    'calendar-no-show-shield',
    'Blue',
    'Reduce meeting no-shows with AI-optimized reminders',
    9900,
    99000,
    '{
      "headline": "Cut Meeting No-Shows by 70%",
      "subheadline": "AI-optimized reminder sequences + urgency triggers",
      "cta": "Activate Shield",
      "features": ["Multi-channel reminders", "Urgency optimization", "Reschedule automation", "No-show prediction"],
      "colors": {"primary": "#059669", "accent": "#10b981"}
    }'::jsonb
  );

-- ============================================
-- SEED DATA - EMAIL TEMPLATES
-- ============================================
INSERT INTO email_templates (template_key, subject, body_html, body_text, variables) VALUES
  (
    'founding_welcome',
    'Welcome to Konqer Founding Members 🚀',
    '<h1>Welcome {{user.name}}!</h1><p>You are now a Konqer Founding Member. Your 3 initial services are unlocked:</p><ul><li>Cold DM Personalizer</li><li>Sales Objection Crusher</li><li>LinkedIn Carousel Forge</li></ul><p>9 more services will unlock over the next 4 weeks. Check your dashboard: <a href="https://konqer.app/dashboard">Dashboard</a></p>',
    'Welcome {{user.name}}! You are now a Konqer Founding Member. Your 3 initial services are unlocked. 9 more services will unlock over the next 4 weeks. Dashboard: https://konqer.app/dashboard',
    '["user.name"]'::jsonb
  ),
  (
    'service_unlocked',
    'New Service Unlocked: {{service.name}} 🎉',
    '<h1>Good news {{user.name}}!</h1><p>Your next Founding Member service is now unlocked:</p><h2>{{service.name}}</h2><p>{{service.description}}</p><p><a href="{{service.url}}">Start using {{service.name}} →</a></p>',
    'Good news {{user.name}}! Your next service is unlocked: {{service.name}}. Start using: {{service.url}}',
    '["user.name", "service.name", "service.description", "service.url"]'::jsonb
  );

-- ============================================
-- VIEWS (Performance Analytics)
-- ============================================

-- MRR calculation view
CREATE VIEW mrr_analytics AS
SELECT
  DATE_TRUNC('month', s.created_at) AS month,
  COUNT(DISTINCT s.user_id) AS active_subscriptions,
  SUM(
    CASE
      WHEN s.plan = 'founding' THEN 699.00 / 12
      WHEN s.plan IN ('monthly_single', 'monthly_bundle') THEN (
        SELECT pricing_monthly::float / 100 FROM service_configs LIMIT 1
      )
      WHEN s.plan IN ('annual_single', 'annual_bundle') THEN (
        SELECT pricing_annual::float / 100 / 12 FROM service_configs LIMIT 1
      )
    END
  ) AS mrr
FROM subscriptions s
WHERE s.status = 'active'
GROUP BY month
ORDER BY month DESC;

-- User lifetime value
CREATE VIEW user_ltv AS
SELECT
  u.id,
  u.email,
  u.created_at,
  COUNT(DISTINCT s.id) AS subscription_count,
  SUM(p.amount)::float / 100 AS total_revenue,
  EXTRACT(DAYS FROM (NOW() - u.created_at)) AS days_active,
  COUNT(g.id) AS total_generations
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id
LEFT JOIN payments p ON u.id = p.user_id AND p.status = 'succeeded'
LEFT JOIN generations g ON u.id = g.user_id
GROUP BY u.id, u.email, u.created_at;

-- Service usage stats
CREATE VIEW service_usage_stats AS
SELECT
  g.service,
  COUNT(DISTINCT g.user_id) AS unique_users,
  COUNT(g.id) AS total_generations,
  AVG(g.personalization_score) AS avg_personalization_score,
  DATE_TRUNC('day', g.created_at) AS date
FROM generations g
GROUP BY g.service, DATE_TRUNC('day', g.created_at)
ORDER BY date DESC, total_generations DESC;

-- ============================================
-- GRANTS (Security)
-- ============================================
-- Create API user (read-write on tables, read-only on views)
-- Note: Execute after creating the konqer_api user
-- CREATE USER konqer_api WITH PASSWORD 'secure_password_from_DO_secrets';
-- GRANT CONNECT ON DATABASE konqer_production TO konqer_api;
-- GRANT USAGE ON SCHEMA public TO konqer_api;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO konqer_api;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA public TO konqer_api;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO konqer_api;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- Version: 001
-- Applied: 2025-10-06
-- Tables: 17
-- Views: 3
-- Indexes: 50+
