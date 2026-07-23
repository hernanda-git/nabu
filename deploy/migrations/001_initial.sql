-- Nabu Initial Migration
-- Creates core tables for the airdrop intelligence system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Core Tables ───

CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    protocol_name VARCHAR(255),
    category VARCHAR(100),
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    overall_score DECIMAL(5,2),
    difficulty_score DECIMAL(3,1),
    estimated_value_usd_min DECIMAL(12,2),
    estimated_value_usd_max DECIMAL(12,2),
    confidence VARCHAR(20),
    verdict VARCHAR(50),
    networks TEXT[],
    risk_level VARCHAR(20),
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    snapshot_date TIMESTAMPTZ,
    claim_start TIMESTAMPTZ,
    claim_end TIMESTAMPTZ,
    tge_date TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_opportunities_score ON opportunities(overall_score DESC);
CREATE INDEX idx_opportunities_status ON opportunities(status);
CREATE INDEX idx_opportunities_detected ON opportunities(detected_at DESC);
CREATE INDEX idx_opportunities_claim_start ON opportunities(claim_start);
CREATE INDEX idx_opportunities_networks ON opportunities USING GIN(networks);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    parameters JSONB,
    is_optional BOOLEAN DEFAULT false,
    estimated_gas_usd DECIMAL(10,2),
    estimated_time_minutes INTEGER,
    difficulty VARCHAR(20),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_opportunity ON tasks(opportunity_id, sort_order);

CREATE TABLE protocol_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    website VARCHAR(500),
    twitter VARCHAR(200),
    discord VARCHAR(200),
    telegram VARCHAR(200),
    github VARCHAR(200),
    whitepaper_url VARCHAR(500),
    fundraising_total DECIMAL(12,2),
    fundraising_rounds JSONB,
    investors TEXT[],
    team_info JSONB,
    audit_reports JSONB,
    tvl DECIMAL(16,2),
    tvl_source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE wallet_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address VARCHAR(42) NOT NULL,
    opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    tasks_completed TEXT[],
    tasks_in_progress TEXT[],
    gas_spent_usd DECIMAL(10,2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'not_started',
    last_activity TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(address, opportunity_id)
);

CREATE INDEX idx_wallet_states_address ON wallet_states(address);
CREATE INDEX idx_wallet_states_status ON wallet_states(status);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42),
    type VARCHAR(50) NOT NULL,
    data JSONB,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_time ON events(occurred_at DESC);
CREATE INDEX idx_events_opportunity ON events(opportunity_id);
CREATE INDEX idx_events_wallet ON events(wallet_address);

-- ─── v2/v3 Extensions ───

CREATE TABLE market_regime (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regime VARCHAR(20) NOT NULL,
    weights JSONB NOT NULL,
    signals JSONB,
    active_from TIMESTAMPTZ DEFAULT NOW(),
    active_until TIMESTAMPTZ
);

CREATE TABLE source_authority (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id VARCHAR(100) NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,
    name VARCHAR(200),
    accuracy DECIMAL(3,2) DEFAULT 0,
    reach DECIMAL(3,2) DEFAULT 0,
    recency DECIMAL(3,2) DEFAULT 0,
    expertise DECIMAL(3,2) DEFAULT 0,
    authority_score DECIMAL(3,2) DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE gas_cost_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,
    source_chain VARCHAR(50),
    target_chain VARCHAR(50),
    route VARCHAR(100) NOT NULL,
    estimated_gas_usd DECIMAL(10,2) NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(task_type, source_chain, target_chain, route)
);

CREATE TABLE historical_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    actual_value_usd DECIMAL(12,2),
    claimed BOOLEAN DEFAULT false,
    claim_tx_hash VARCHAR(66),
    scam BOOLEAN DEFAULT false,
    score_predicted DECIMAL(5,2),
    value_predicted_min DECIMAL(12,2),
    value_predicted_max DECIMAL(12,2),
    scoring_weights JSONB,
    regime_at_time VARCHAR(20),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_historical_outcomes_opp ON historical_outcomes(opportunity_id);

CREATE TABLE mining_machines (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'idle',
    egress_cidr TEXT[],
    current_task VARCHAR(100),
    total_gas_usd DECIMAL(12,2) DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0,
    last_heartbeat TIMESTAMPTZ,
    registered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_type VARCHAR(50) NOT NULL,
    protocol_name VARCHAR(255) NOT NULL,
    chain VARCHAR(50),
    z_score DECIMAL(5,2),
    confidence DECIMAL(3,2),
    recommended_watch BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_leads_protocol ON leads(protocol_name);
CREATE INDEX idx_leads_created ON leads(created_at DESC);

-- ─── Functions ───

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_opportunities_updated_at BEFORE UPDATE ON opportunities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_protocol_info_updated_at BEFORE UPDATE ON protocol_info
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallet_states_updated_at BEFORE UPDATE ON wallet_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();