#  Quick Start Guide

## Prerequisites

Before running the application, make sure you have:

- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Python 3.9+** - [Download here](https://python.org/)
- **PostgreSQL 14+** - [Download here](https://postgresql.org/)
- **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)

## 🎯 Option 1: Automated Setup (Recommended)

Run the setup script to automatically configure everything:

```bash
./setup.sh
```

This will:
-  Check system requirements
-  Install all dependencies
-  Set up the database
-  Create environment files
-  Configure everything for you

## 🛠️ Option 2: Manual Setup

### 1. Install Dependencies

```bash
# Backend
cd backend
npm install

# Python Service
cd ../python-service
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Set Up Database

```bash
# Create database
createdb appointment_chatbot

# Run schema and sample data
psql appointment_chatbot < database/schema.sql
psql appointment_chatbot < database/sample_data.sql
```

### 3. Configure Environment Variables

Copy and update the environment files:

```bash
# Backend
cp backend/env.example backend/.env
# Edit backend/.env with your database credentials

# Python Service
cp python-service/env.example python-service/.env
# Edit python-service/.env with your OpenAI API key

# Frontend
cp frontend/env.local.example frontend/.env.local
# Edit frontend/.env.local if needed
```

##  Running the Application

### Option A: Individual Services

```bash
# Terminal 1 - Backend API
cd backend
npm run dev

# Terminal 2 - Python AI Service
cd python-service
python app.py

# Terminal 3 - Frontend
cd frontend
npm run dev
```

### Option B: Docker Compose (Easiest)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🌐 Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:3001
- **Python AI Service**: http://localhost:5000
- **Database**: localhost:5432

##  Testing the System

1. **Open the application** at http://localhost:3000
2. **Create an account** or login
3. **Start chatting** with the AI assistant
4. **Try these commands**:
   - "I want to book an appointment"
   - "Check my appointments"
   - "Reschedule my appointment"
   - "What are your office hours?"

## 🔧 Troubleshooting

### Common Issues:

1. **Database Connection Error**
   ```bash
   # Make sure PostgreSQL is running
   brew services start postgresql  # macOS
   sudo service postgresql start   # Linux
   ```

2. **OpenAI API Error**
   - Check your API key in `python-service/.env`
   - Ensure you have credits in your OpenAI account

3. **Port Already in Use**
   ```bash
   # Kill processes using ports
   lsof -ti:3000,3001,5000 | xargs kill -9
   ```

4. **Permission Denied**
   ```bash
   # Make setup script executable
   chmod +x setup.sh
   ```

### Logs and Debugging:

- **Backend logs**: `backend/logs/`
- **Python logs**: `python-service/logs/`
- **Docker logs**: `docker-compose logs`

## 📱 Features to Test

### Chat Interface
-  Real-time messaging
-  Typing indicators
-  Message history
-  Quick action buttons

### Authentication
-  User registration
-  Login/logout
-  Session management
-  Protected routes

### Appointment Booking
-  Book new appointments
-  View existing appointments
-  Reschedule appointments
-  Cancel appointments

### AI Features
-  Natural language processing
-  Intent classification
-  Entity extraction
-  Conversation flow management

## 🎯 Next Steps

Once everything is running:

1. **Explore the chat interface** - Try different appointment requests
2. **Test user authentication** - Create accounts and login
3. **Check the database** - View the data in PostgreSQL
4. **Monitor the logs** - See how the AI processes messages
5. **Customize the system** - Modify prompts, add features

## 🆘 Need Help?

If you encounter any issues:

1. Check the logs in the respective service directories
2. Ensure all environment variables are set correctly
3. Verify that all services are running on the correct ports
4. Check the database connection and data

## 🎉 Success!

You should now have a fully functional AI-powered appointment booking chatbot system running locally!

The system demonstrates:
- Modern web architecture
- AI integration with LangChain
- Real-time communication
- Database management
- User authentication
- Responsive design
