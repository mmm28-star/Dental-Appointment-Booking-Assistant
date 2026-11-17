# Dental Appointment Booking Assistant

A full-stack project that uses AI to book and manage dental appointments, powered by LangChain and a modern web stack.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Simple Frontend│    │  Node.js API    │    │ Python Service  │
│   (HTML/Alpine) │◄──►│   (Express)     │◄──►│   (LangChain)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   OpenAI API    │    │   Database      │
│   Database      │    │   (GPT-4)       │    │   Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start & Demo

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL 14+
- OpenAI API Key

### Demo Commands (Run in Order)

**1. Start PostgreSQL:**
```bash
brew services start postgresql@14
```

**2. Setup Database:**
```bash
# Create database
createdb appointment_chatbot

# Run schema and sample data
psql appointment_chatbot < database/schema.sql
psql appointment_chatbot < database/sample_data.sql
```

**3. Start Backend API (Terminal 1):**
```bash
cd backend
npm install
cp env.example .env
# Edit .env with your database credentials
npm start
```

**4. Start Python Service (Terminal 2):**
```bash
cd python-service
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edit .env with your OpenAI API key
python app.py
```

**5. Start Frontend (Terminal 3):**
```bash
cd simple-frontend
python3 -m http.server 3000
```

**6. Access the Application:**
- Open browser: http://localhost:3000
- Start chatting with the AI assistant!

### Run Everything with One Command
```bash
# Start all services together
./start_demo.sh

# Stop all services
./stop_demo.sh
```

### Sample Chat Scenarios

1. **Book an Appointment:**
   - "I want to book a dental cleaning for tomorrow at 2pm with Dr. Sarah. My name is John Smith."

2. **Check Appointments:**
   - "I want to check my previous appointments"
   - Provide your name when asked

3. **Reschedule Appointment:**
   - "I want to reschedule my appointment"
   - Provide your name and new date/time

### Environment Setup

**Backend (.env):**
```
DATABASE_URL=postgresql://username:password@localhost:5432/appointment_chatbot
JWT_SECRET=your-jwt-secret
PYTHON_SERVICE_URL=http://localhost:5001
PORT=3001
```

**Python Service (.env):**
```
OPENAI_API_KEY=your-openai-api-key
DATABASE_URL=postgresql://username:password@localhost:5432/appointment_chatbot
FLASK_ENV=development
FLASK_PORT=5001
```

## Repository Structure

```
Assessment/
├── backend/                 # Node.js/Express API
│   ├── src/
│   │   ├── controllers/     # API controllers
│   │   ├── middleware/      # Auth, validation, logging
│   │   ├── models/         # Database models
│   │   ├── routes/         # API routes
│   │   └── utils/          # Helper functions
│   ├── package.json
│   └── .env.example
├── python-service/         # LangChain microservice
│   ├── app.py             # Main Flask application
│   ├── chatbot/           # Chatbot logic
│   ├── utils/              # Database utilities
│   ├── requirements.txt
│   └── .env.example
├── simple-frontend/        # Simple HTML frontend
│   └── index.html          # Chat interface
├── database/               # Database schema and migrations
│   ├── schema.sql
│   └── sample_data.sql
├── setup.sh               # Automated setup script
├── QUICK_START.md         # Quick start guide
└── README.md              # This file
```


## Key Capabilities

### Frontend (Simple HTML)
-  Real-time chat interface with Alpine.js
-  Clean and responsive design
-  Direct integration with Python service
-  Session management
-  Chat history and conversation persistence

### Backend API (Node.js/Express)
-  RESTful API with proper error handling
-  JWT-based authentication system
-  Rate limiting and request validation
-  WebSocket support for real-time communication
-  Database integration with PostgreSQL

### Python Microservice (LangChain)
-  LangChain integration with OpenAI GPT-4
-  Conversation flow management
-  Appointment scheduling logic
-  Natural language processing for intent recognition
-  Integration with external calendar APIs

### Database (PostgreSQL)
-  Optimized schema for users, appointments, and chat sessions
-  Proper indexing for performance
-  Sample data for testing
-  Migration scripts for easy setup

## Demo Scripts

- `./start_demo.sh` - Start all services automatically
- `./stop_demo.sh` - Stop all services
- `DEMO_GUIDE.md` - Complete demo scenarios and troubleshooting



