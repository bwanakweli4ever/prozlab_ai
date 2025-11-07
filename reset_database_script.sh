#!/bin/bash
# Complete Database Reset Script - Handles foreign key dependencies properly

echo "🚀 Starting complete database reset..."

# Step 1: Stop any running migrations and clean up
echo "🧹 Cleaning up existing migrations..."
rm -f migrations/versions/*.py
touch migrations/versions/__init__.py

# Step 2: Reset the database completely
echo "🗑️  Resetting database (with CASCADE to handle dependencies)..."
PGPASSWORD='Root@2022' psql -d prozlab_db -U proz_user <<'EOF'

-- Drop all tables with CASCADE to handle foreign key dependencies
DROP TABLE IF EXISTS task_notifications CASCADE;
DROP TABLE IF EXISTS task_assignments CASCADE;
DROP TABLE IF EXISTS service_requests CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS proz_specialty CASCADE;
DROP TABLE IF EXISTS proz_profiles CASCADE;
DROP TABLE IF EXISTS specialties CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop custom types
DROP TYPE IF EXISTS task_status CASCADE;
DROP TYPE IF EXISTS task_priority CASCADE;
DROP TYPE IF EXISTS verification_status CASCADE;

-- Drop the alembic version table to reset migration history
DROP TABLE IF EXISTS alembic_version CASCADE;

-- Recreate schema fresh
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO proz_user;
GRANT ALL ON SCHEMA public TO public;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

SELECT 'Database completely reset!' as result;

EOF

echo "✅ Database reset complete"

# Step 3: Create fresh database schema
echo "🏗️  Creating fresh database schema..."
psql -d prozlab_db -U proz_user << 'EOF'

-- Create ENUM types first
CREATE TYPE task_status AS ENUM ('pending', 'assigned', 'accepted', 'in_progress', 'completed', 'cancelled', 'rejected');
CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'urgent');

-- Users table (base table - no dependencies)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Specialties table (independent)
CREATE TABLE specialties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Professional profiles table (depends on users)
CREATE TABLE proz_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    profile_image_url VARCHAR(500),
    bio TEXT,
    location VARCHAR(255),
    years_experience INTEGER,
    hourly_rate DECIMAL(10,2),
    availability VARCHAR(50),
    education TEXT,
    certifications TEXT,
    website VARCHAR(255),
    linkedin VARCHAR(255),
    preferred_contact_method VARCHAR(50) DEFAULT 'email',
    verification_status VARCHAR(20) DEFAULT 'pending',
    is_featured BOOLEAN DEFAULT FALSE,
    rating DECIMAL(3,2) DEFAULT 0.00,
    review_count INTEGER DEFAULT 0,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Junction table for proz profiles and specialties
CREATE TABLE proz_specialty (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    specialty_id UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(proz_id, specialty_id)
);

-- Reviews table (depends on proz_profiles)
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    client_name VARCHAR(100) NOT NULL,
    client_email VARCHAR(255),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Service requests table (independent)
CREATE TABLE service_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(200) NOT NULL,
    client_name VARCHAR(100) NOT NULL,
    client_email VARCHAR(255) NOT NULL,
    client_phone VARCHAR(20),
    service_title VARCHAR(200) NOT NULL,
    service_description TEXT NOT NULL,
    service_category VARCHAR(100) NOT NULL,
    required_skills TEXT,
    budget_min DECIMAL(10,2),
    budget_max DECIMAL(10,2),
    expected_duration VARCHAR(100),
    deadline TIMESTAMP WITH TIME ZONE,
    location_preference VARCHAR(255),
    remote_work_allowed BOOLEAN DEFAULT TRUE,
    status task_status DEFAULT 'pending' NOT NULL,
    priority task_priority DEFAULT 'medium' NOT NULL,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task assignments table (depends on service_requests and proz_profiles)
CREATE TABLE task_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_request_id UUID NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    assigned_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    assignment_notes TEXT,
    estimated_hours DECIMAL(8,2),
    proposed_rate DECIMAL(10,2),
    status task_status DEFAULT 'assigned' NOT NULL,
    proz_response TEXT,
    proz_response_at TIMESTAMP WITH TIME ZONE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(service_request_id, proz_id)
);

-- Task notifications table (depends on proz_profiles and task_assignments)
CREATE TABLE task_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    task_assignment_id UUID REFERENCES task_assignments(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    is_email_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_proz_profiles_email ON proz_profiles(email);
CREATE INDEX idx_proz_profiles_user_id ON proz_profiles(user_id);
CREATE INDEX idx_proz_profiles_verification ON proz_profiles(verification_status);
CREATE INDEX idx_proz_profiles_featured ON proz_profiles(is_featured);
CREATE INDEX idx_reviews_proz_id ON reviews(proz_id);
CREATE INDEX idx_reviews_approved ON reviews(is_approved);
CREATE INDEX idx_service_requests_status ON service_requests(status);
CREATE INDEX idx_service_requests_priority ON service_requests(priority);
CREATE INDEX idx_task_assignments_proz_id ON task_assignments(proz_id);
CREATE INDEX idx_task_assignments_status ON task_assignments(status);
CREATE INDEX idx_task_notifications_proz_id ON task_notifications(proz_id);
CREATE INDEX idx_task_notifications_read ON task_notifications(is_read);

-- Insert default specialties
INSERT INTO specialties (name, description) VALUES
('Web Development', 'Frontend and backend web development'),
('Mobile Development', 'iOS and Android app development'),
('UI/UX Design', 'User interface and experience design'),
('Digital Marketing', 'SEO, social media, and online marketing'),
('Data Science', 'Data analysis and machine learning'),
('DevOps', 'Cloud infrastructure and deployment'),
('Graphic Design', 'Visual design and branding'),
('Content Writing', 'Copywriting and content creation'),
('Project Management', 'Project planning and coordination'),
('Consulting', 'Business and technical consulting');

-- Create admin user (password: admin123)
-- Hash generated with bcrypt: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeRQdOkSMWL.ZYPYm
INSERT INTO users (email, hashed_password, first_name, last_name, is_superuser, is_active, is_verified) VALUES
('admin@prozlab.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeRQdOkSMWL.ZYPYm', 'Admin', 'User', true, true, true);

-- Create a test professional profile linked to admin
INSERT INTO proz_profiles (user_id, email, first_name, last_name, bio, location, years_experience, hourly_rate, availability, verification_status, is_featured)
SELECT id, email, first_name, last_name, 'System Administrator and Platform Manager', 'Remote', 5, 100.00, 'part-time', 'verified', true
FROM users WHERE email = 'admin@prozlab.com';

SELECT 'Fresh database schema created successfully!' as result;
SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'public';
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

EOF

echo "✅ Fresh database schema created"

# Step 4: Reinitialize Alembic and create initial migration
echo "🔧 Reinitializing Alembic..."

# Create the initial migration to match current state
alembic stamp base
alembic revision --autogenerate -m "Initial database schema"
alembic stamp head

echo "✅ Alembic reinitialized"

# Step 5: Verify everything is working
echo "🔍 Verifying setup..."
echo "Database tables:"
psql -d prozlab_db -U proz_user -c "\dt"

echo ""
echo "Alembic current revision:"
alembic current

echo ""
echo "Migration files:"
ls -la migrations/versions/

echo ""
echo "Testing database connection and admin user:"
psql -d prozlab_db -U proz_user -c "SELECT email, first_name, last_name, is_superuser FROM users WHERE email = 'admin@prozlab.com';"

echo ""
echo "🎉 Complete database reset finished successfully!"
echo "📋 Default admin user: admin@prozlab.com / admin123"
echo "🚀 You can now start your FastAPI server and test registration!"