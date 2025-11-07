#!/bin/bash
# Fixed Database Migration Script

echo "🚀 Fixing database schema issues..."

# Step 1: Create/Update the database schema
echo "🔧 Updating database schema..."
psql -d prozlab_db -U proz_user << 'EOF'

-- Drop existing tables if they exist (careful!)
DROP TABLE IF EXISTS task_notifications CASCADE;
DROP TABLE IF EXISTS task_assignments CASCADE;
DROP TABLE IF EXISTS service_requests CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS proz_specialty CASCADE;
DROP TABLE IF EXISTS proz_profiles CASCADE;
DROP TABLE IF EXISTS specialties CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop types if they exist
DROP TYPE IF EXISTS task_status CASCADE;
DROP TYPE IF EXISTS task_priority CASCADE;
DROP TYPE IF EXISTS verification_status CASCADE;

-- Create ENUM types
CREATE TYPE task_status AS ENUM ('pending', 'assigned', 'accepted', 'in_progress', 'completed', 'cancelled', 'rejected');
CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'urgent');
CREATE TYPE verification_status AS ENUM ('pending', 'verified', 'rejected');

-- Users table (corrected)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Specialties table
CREATE TABLE specialties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Professional profiles table (corrected with user_id FK)
CREATE TABLE proz_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
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

-- Professional specialties junction table
CREATE TABLE proz_specialty (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    specialty_id UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(proz_id, specialty_id)
);

-- Reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    client_name VARCHAR(100) NOT NULL,
    client_email VARCHAR(255),
    rating INTEGER NOT NULL,
    review_text TEXT,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Service requests table
CREATE TABLE service_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Task assignments table
CREATE TABLE task_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_request_id UUID NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    proz_id UUID NOT NULL REFERENCES proz_profiles(id) ON DELETE CASCADE,
    assigned_by_user_id UUID REFERENCES users(id),
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

-- Task notifications table
CREATE TABLE task_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_proz_profiles_email ON proz_profiles(email);
CREATE INDEX idx_proz_profiles_user_id ON proz_profiles(user_id);
CREATE INDEX idx_proz_profiles_verification_status ON proz_profiles(verification_status);
CREATE INDEX idx_service_requests_status ON service_requests(status);
CREATE INDEX idx_task_assignments_proz_id ON task_assignments(proz_id);
CREATE INDEX idx_task_notifications_proz_id ON task_notifications(proz_id);

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
-- Hash for 'admin123': $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeRQdOkSMWL.ZYPYm
INSERT INTO users (email, hashed_password, first_name, last_name, is_superuser, is_active, is_verified) VALUES
('admin@prozlab.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeRQdOkSMWL.ZYPYm', 'Admin', 'User', true, true, true);

SELECT 'Database schema updated successfully!' as result;
SELECT 'Tables created:' as info;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

EOF

echo "✅ Database schema updated successfully!"

# Step 2: Reset Alembic to match current state
echo "🔄 Resetting Alembic..."
rm -f migrations/versions/*.py
touch migrations/versions/__init__.py

# Create new migration
echo "📝 Creating new migration..."
alembic revision --autogenerate -m "Fixed database schema with proper relationships"

# Mark as applied
echo "✅ Marking migration as applied..."
alembic upgrade head

echo "🎉 Database fix completed successfully!"
echo "📋 You can now test registration with: admin@prozlab.com / admin123"