-- Migration: Add is_guest column to users table
-- Purpose: Support guest/demo accounts with automatic cleanup
-- Date: 2026-07-15

-- Add is_guest column with default FALSE for existing users
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE NOT NULL;

-- Create index for faster guest account queries (used by cleanup script)
CREATE INDEX IF NOT EXISTS idx_users_is_guest_created 
ON users(is_guest, created_at) 
WHERE is_guest = TRUE;

-- Verify migration
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='is_guest'
    ) THEN
        RAISE EXCEPTION 'Migration failed: is_guest column not found';
    END IF;
END $$;
