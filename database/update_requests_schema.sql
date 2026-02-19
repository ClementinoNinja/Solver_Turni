-- Add note column to requests table
ALTER TABLE requests 
ADD COLUMN IF NOT EXISTS note TEXT;
