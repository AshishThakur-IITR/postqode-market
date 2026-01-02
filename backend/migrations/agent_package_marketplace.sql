-- ============================================
-- PostQode Agent Package Marketplace Migration
-- Run this script against your PostgreSQL database
-- ============================================

-- Add package fields to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS manifest_yaml TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS package_url VARCHAR(500);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS package_checksum VARCHAR(64);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS package_size_bytes INTEGER;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS supported_runtimes JSONB DEFAULT '[]';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS required_permissions JSONB DEFAULT '{}';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS min_runtime_version VARCHAR(20);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS inputs_schema JSONB DEFAULT '[]';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS outputs_schema JSONB DEFAULT '[]';

-- Add is_publisher flag to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_publisher BOOLEAN DEFAULT false;

-- Create agent_adapters table
CREATE TABLE IF NOT EXISTS agent_adapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    adapter_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    config_yaml TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on agent_adapters
CREATE INDEX IF NOT EXISTS idx_agent_adapters_agent_id ON agent_adapters(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_adapters_type ON agent_adapters(adapter_type);

-- Create deployment_type enum
DO $$ BEGIN
    CREATE TYPE deployment_type AS ENUM (
        'cloud_managed',
        'kubernetes',
        'vm_standalone',
        'serverless',
        'edge',
        'docker'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create deployment_status enum
DO $$ BEGIN
    CREATE TYPE deployment_status AS ENUM (
        'pending',
        'active',
        'stopped',
        'error',
        'updating'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create agent_deployments table
CREATE TABLE IF NOT EXISTS agent_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID NOT NULL REFERENCES licenses(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    user_id UUID NOT NULL REFERENCES users(id),
    deployment_type VARCHAR(50) NOT NULL,
    adapter_used VARCHAR(50),
    deployment_config JSONB DEFAULT '{}',
    environment_name VARCHAR(100),
    runtime_version VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    error_message VARCHAR(500),
    deployed_at TIMESTAMP DEFAULT NOW(),
    last_health_check TIMESTAMP,
    stopped_at TIMESTAMP,
    total_invocations INTEGER DEFAULT 0,
    last_invocation TIMESTAMP
);

-- Create indexes on agent_deployments
CREATE INDEX IF NOT EXISTS idx_agent_deployments_user_id ON agent_deployments(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_deployments_agent_id ON agent_deployments(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_deployments_license_id ON agent_deployments(license_id);
CREATE INDEX IF NOT EXISTS idx_agent_deployments_status ON agent_deployments(status);

-- Create storage directory for packages (info only - needs to be done on filesystem)
-- mkdir -p ./storage/packages

-- ============================================
-- Verification queries (run after migration)
-- ============================================

-- Check new columns on agents table
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'agents';

-- Check new tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- ============================================
-- Done!
-- ============================================
