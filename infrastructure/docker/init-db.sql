-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create a test database for automated tests
CREATE DATABASE scr_platform_test;
GRANT ALL PRIVILEGES ON DATABASE scr_platform_test TO scr_user;
