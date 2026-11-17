#!/bin/bash

# This script sets up the complete development environment

set -e

echo " Setting up  Appointment Booking Chatbot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking system requirements..."

    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org/"
        exit 1
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9+ from https://python.org/"
        exit 1
    fi

    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        print_error "PostgreSQL is not installed. Please install PostgreSQL from https://postgresql.org/"
        exit 1
    fi

    print_success "All requirements are met!"
}

# Setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."

    # Backend environment
    if [ ! -f "backend/.env" ]; then
        cp backend/env.example backend/.env
        print_success "Created backend/.env file"
    else
        print_warning "backend/.env already exists, skipping..."
    fi

    # Python service environment
    if [ ! -f "python-service/.env" ]; then
        cp python-service/env.example python-service/.env
        print_success "Created python-service/.env file"
    else
        print_warning "python-service/.env already exists, skipping..."
    fi

    # Frontend environment
    if [ ! -f "frontend/.env.local" ]; then
        cp frontend/env.local.example frontend/.env.local
        print_success "Created frontend/.env.local file"
    else
        print_warning "frontend/.env.local already exists, skipping..."
    fi

    print_warning "Please update the environment files with your actual values:"
    print_warning "- Add your OpenAI API key to python-service/.env"
    print_warning "- Update database credentials in backend/.env"
}

# Install backend dependencies
setup_backend() {
    print_status "Setting up backend dependencies..."

    cd backend
    npm install
    cd ..

    print_success "Backend dependencies installed"
}

# Install Python dependencies
setup_python() {
    print_status "Setting up Python dependencies..."

    cd python-service
    pip install -r requirements.txt
    cd ..

    print_success "Python dependencies installed"
}

# Install frontend dependencies
setup_frontend() {
    print_status "Setting up frontend dependencies..."

    cd frontend
    npm install
    cd ..

    print_success "Frontend dependencies installed"
}

# Setup database
setup_database() {
    print_status "Setting up database..."

    # Create database if it doesn't exist
    createdb appointment_chatbot 2>/dev/null || print_warning "Database 'appointment_chatbot' might already exist"

    # Run schema and sample data
    psql appointment_chatbot < database/schema.sql
    psql appointment_chatbot < database/sample_data.sql

    print_success "Database setup completed"
}

# Create logs directories
setup_logs() {
    print_status "Creating logs directories..."

    mkdir -p backend/logs
    mkdir -p python-service/logs
    mkdir -p frontend/logs

    print_success "Logs directories created"
}

# Main setup function
main() {
    echo "=========================================="
    echo "  AI-Powered Appointment Booking Chatbot"
    echo "  Setup Script"
    echo "=========================================="
    echo ""

    check_requirements
    setup_environment
    setup_logs
    setup_database
    setup_backend
    setup_python
    setup_frontend

    echo ""
    echo "=========================================="
    print_success "Setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Update environment variables in the .env files"
    echo "2. Start the services:"
    echo "   - Backend: cd backend && npm run dev"
    echo "   - Python: cd python-service && python app.py"
    echo "   - Frontend: cd frontend && npm run dev"
    echo ""
    echo "Or use Docker Compose:"
    echo "   docker-compose up -d"
    echo ""
    echo "Access the application at: http://localhost:3000"
    echo ""
}

# Run main function
main "$@"
