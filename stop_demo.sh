#!/bin/bash

# Stop all demo services

echo " Stopping  Appointment Booking Chatbot Demo"
echo "====================================================="

# Function to stop service
stop_service() {
    local name=$1
    local pid_file="${name,,}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $name (PID: $pid)..."
            kill "$pid"
            rm "$pid_file"
            echo " $name stopped"
        else
            echo "⚠️  $name was not running"
            rm "$pid_file"
        fi
    else
        echo "⚠️  No PID file found for $name"
    fi
}

# Stop all services
stop_service "Backend"
stop_service "Python-Service"
stop_service "Frontend"

# Kill any remaining processes
echo ""
echo "🧹 Cleaning up any remaining processes..."

# Kill Node.js processes on port 3001
pkill -f "node.*app.js" 2>/dev/null || true

# Kill Python processes on port 5001
pkill -f "python.*app.py" 2>/dev/null || true

# Kill Python HTTP server on port 3000
pkill -f "python3.*http.server.*3000" 2>/dev/null || true

echo " All services stopped"
echo ""
echo "💡 To start the demo again, run: ./start_demo.sh"
