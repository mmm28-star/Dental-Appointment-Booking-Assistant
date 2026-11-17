# 🎬 Demo Guide - AI-Powered Appointment Booking Chatbot

## Quick Start (3 Commands)

### 1. Start All Services
```bash
./start_demo.sh
```

### 2. Open Application
- Go to: http://localhost:3000
- Start chatting with the AI assistant!

### 3. Stop All Services
```bash
./stop_demo.sh
```

---

## 🎯 Demo Scenarios

### Scenario 1: Book an Appointment
**User:** "I want to book a dental cleaning for tomorrow at 2pm with Dr. Sarah. My name is John Smith."

**Expected Response:**
- Confirmation with appointment details
- Patient name, type, date, time, doctor
- Email and phone information

### Scenario 2: Check Previous Appointments
**User:** "I want to check my previous appointments"
**Bot:** "Sure, can you please provide me with your full name?"
**User:** "John Smith"
**Bot:** Shows list of appointments for John Smith

### Scenario 3: Reschedule Appointment
**User:** "I want to reschedule my appointment"
**Bot:** "I'd be happy to help you reschedule an appointment! First, could you please provide your name so I can look up your appointments?"
**User:** "John Smith"
**Bot:** Shows available appointments and asks for new date/time
**User:** "Reschedule it for next Friday at 3pm"
**Bot:** Confirms the rescheduling

---

## 🔧 Manual Setup (If Scripts Don't Work)

### Terminal 1 - Backend API
```bash
cd backend
npm install
cp env.example .env
# Edit .env with your database credentials
npm start
```

### Terminal 2 - Python Service
```bash
cd python-service
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edit .env with your OpenAI API key
python app.py
```

### Terminal 3 - Frontend
```bash
cd simple-frontend
python3 -m http.server 3000
```

---

## 🐛 Troubleshooting

### Database Issues
```bash
# Check if PostgreSQL is running
brew services start postgresql@14

# Create database if needed
createdb appointment_chatbot
psql appointment_chatbot < database/schema.sql
psql appointment_chatbot < database/sample_data.sql
```

### Port Conflicts
- Backend: Port 3001
- Python Service: Port 5001
- Frontend: Port 3000

### Environment Variables
Make sure you have:
- OpenAI API key in `python-service/.env`
- Database credentials in `backend/.env`

---

## 📱 Demo Tips

1. **Start with a booking** - Shows the full AI capability
2. **Use realistic names** - Makes the demo more believable
3. **Try different appointment types** - Shows flexibility
4. **Test the conversation flow** - Shows context awareness
5. **Show the database persistence** - Refresh and check appointments

---

## 🎉 Key Features to Highlight

-  **AI-Powered**: Uses OpenAI GPT-4 for natural language understanding
-  **Context Aware**: Remembers conversation history
-  **Database Integration**: Real PostgreSQL storage
-  **Multi-turn Conversations**: Handles complex booking flows
-  **Intent Recognition**: Understands booking, checking, rescheduling
-  **Entity Extraction**: Extracts names, dates, times, doctors
-  **Error Handling**: Graceful fallbacks and user guidance
