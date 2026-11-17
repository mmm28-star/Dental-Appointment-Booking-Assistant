#!/bin/bash

# This script starts all services for the demo

echo " Starting AI-Powered Appointment Booking Chatbot Demo"
echo "=================================================="

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start it first:"
    echo "   brew services start postgresql@14"
    exit 1
fi

# Check if database exists
if ! psql -lqt | cut -d \| -f 1 | grep -qw appointment_chatbot; then
    echo "📊 Setting up database..."
    createdb appointment_chatbot
    psql appointment_chatbot < database/schema.sql
    psql appointment_chatbot < database/sample_data.sql
    echo " Database setup complete"
fi

echo ""
echo "🎯 Starting services..."
echo ""

# Function to start service in background
start_service() {
    local name=$1
    local dir=$2
    local cmd=$3

    echo "Starting $name..."
    cd "$dir"
    $cmd &
    local pid=$!
    echo "$name started with PID $pid"
    echo "$pid" > "../${name,,}.pid"
    cd ..
    sleep 2
}

# Start Backend API
start_service "Backend" "backend" "npm start"

# Start Python Service
start_service "Python-Service" "python-service" "source ../venv/bin/activate && python app.py"

# Start Frontend
start_service "Frontend" "simple-frontend" "python3 -m http.server 3000"

echo ""
echo "🎉 All services started!"
echo ""
echo "📱 Access the application at: http://localhost:3000"
echo ""
echo " To stop all services, run: ./stop_demo.sh"
echo ""
echo "🎬 Demo Flow:"
echo "1. Book: 'I want to book a dental cleaning for tomorrow at 2pm with Dr. Sarah. My name is John Smith.'"
echo "2. Check: 'I want to check my previous appointments'"
echo "3. Reschedule: 'I want to reschedule my appointment'"
echo ""
echo "Press Ctrl+C to stop this script (services will continue running)"
echo ""

# Wait for user to stop
trap 'echo "Script stopped. Services are still running. Use ./stop_demo.sh to stop them."; exit' INT
while true; do
    sleep 1
done
