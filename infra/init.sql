-- RSS Bot Platform - Database Initialization Script
-- This script sets up the initial database schema and data

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial admin user if using PostgreSQL
-- Note: SQLModel will handle table creation automatically

-- Insert sample data for development (optional)
-- This will be executed only if the tables exist

DO $$
BEGIN
    -- Check if User table exists and insert sample data
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user') THEN
        INSERT INTO "user" (telegram_id, username, first_name, last_name, language_code, subscription_level, created_at)
        VALUES 
            (123456789, 'admin_user', 'Admin', 'User', 'en', 'enterprise', NOW()),
            (987654321, 'test_user', 'Test', 'User', 'en', 'free', NOW())
        ON CONFLICT (telegram_id) DO NOTHING;
        
        RAISE NOTICE 'Sample users inserted successfully';
    ELSE
        RAISE NOTICE 'User table not found, skipping sample data insertion';
    END IF;

    -- Check if Channel table exists and insert sample data
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'channel') THEN
        INSERT INTO "channel" (telegram_id, title, username, description, is_active, owner_id, created_at)
        VALUES 
            (-1001234567890, 'RSS Test Channel', 'rss_test_channel', 'Channel for testing RSS feeds', true, 1, NOW()),
            (-1009876543210, 'News Channel', 'news_channel', 'General news channel', true, 1, NOW())
        ON CONFLICT (telegram_id) DO NOTHING;
        
        RAISE NOTICE 'Sample channels inserted successfully';
    ELSE
        RAISE NOTICE 'Channel table not found, skipping sample data insertion';
    END IF;

END $$;