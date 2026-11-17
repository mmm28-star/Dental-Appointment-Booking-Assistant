"""
AI-Powered Appointment Booking Chatbot Service
Python microservice using LangChain for natural language processing
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import structlog

from chatbot.appointment_bot import AppointmentBot
from chatbot.intent_classifier import IntentClassifier
from chatbot.entity_extractor import EntityExtractor
from chatbot.conversation_manager import ConversationManager
from utils.database import DatabaseManager
from utils.logger import setup_logging
from utils.validators import validate_request, validate_session

# Configure structured logging
setup_logging()
logger = structlog.get_logger()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)
limiter.init_app(app)

# Initialize components
db_manager = DatabaseManager()

# Create a temporary bot to get the LLM
temp_bot = AppointmentBot(
    intent_classifier=None,
    entity_extractor=None,
    conversation_manager=None,
    db_manager=db_manager
)

# Initialize LLM-based components with the LLM from the bot
intent_classifier = IntentClassifier(llm=temp_bot.llm)
entity_extractor = EntityExtractor(llm=temp_bot.llm)
conversation_manager = ConversationManager()

# Create the final bot with LLM-based components
appointment_bot = AppointmentBot(
    intent_classifier=intent_classifier,
    entity_extractor=entity_extractor,
    conversation_manager=conversation_manager,
    db_manager=db_manager
)

@app.before_request
def before_request():
    """Log incoming requests"""
    logger.info(
        "Incoming request",
        method=request.method,
        url=request.url,
        remote_addr=request.remote_addr,
        user_agent=request.headers.get('User-Agent', 'Unknown')
    )

@app.after_request
def after_request(response):
    """Log outgoing responses"""
    logger.info(
        "Outgoing response",
        status_code=response.status_code,
        content_length=response.content_length
    )
    return response

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'timestamp': datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error("Internal server error", error=str(error))
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.utcnow().isoformat()
    }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'components': {
            'database': db_manager.is_connected(),
            'openai': appointment_bot.is_openai_available(),
            'langchain': appointment_bot.is_langchain_available(),
            'intent_classifier': intent_classifier.is_ready(),
            'entity_extractor': entity_extractor.is_ready()
        }
    })

@app.route('/chat', methods=['POST'])
@limiter.limit("60 per minute")
def chat():
    """
    Main chat endpoint for processing user messages
    """
    try:
        # Extract request data
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('sessionId')
        user_id = data.get('userId')
        language = data.get('language', 'en')
        metadata = data.get('metadata', {})

        if not message:
            return jsonify({
                'error': 'Message is required',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        if not session_id:
            return jsonify({
                'error': 'Session ID is required',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(
            "Processing chat message",
            session_id=session_id,
            user_id=user_id,
            message_length=len(message),
            language=language
        )

        # Process the message through the appointment bot
        response = appointment_bot.process_message(
            message=message,
            session_id=session_id,
            user_id=user_id,
            language=language,
            metadata=metadata
        )

        logger.info(
            "Chat response generated",
            session_id=session_id,
            intent=response.get('intent'),
            confidence=response.get('confidence'),
            response_length=len(response.get('response', ''))
        )

        return jsonify({
            'response': response['response'],
            'intent': response['intent'],
            'entities': response['entities'],
            'confidence': response['confidence'],
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': response.get('metadata', {})
        })

    except Exception as e:
        logger.error("Error processing chat message", error=str(e), session_id=session_id)
        return jsonify({
            'error': 'Failed to process message',
            'message': 'An error occurred while processing your request',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/intent', methods=['POST'])
@limiter.limit("100 per minute")
def classify_intent():
    """
    Classify user intent from message
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({
                'error': 'Message is required',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        intent_result = intent_classifier.classify(message)

        return jsonify({
            'intent': intent_result['intent'],
            'confidence': intent_result['confidence'],
            'alternatives': intent_result.get('alternatives', []),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Error classifying intent", error=str(e))
        return jsonify({
            'error': 'Failed to classify intent',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/entities', methods=['POST'])
@limiter.limit("100 per minute")
def extract_entities():
    """
    Extract entities from user message
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({
                'error': 'Message is required',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        entities = entity_extractor.extract(message)

        return jsonify({
            'entities': entities,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Error extracting entities", error=str(e))
        return jsonify({
            'error': 'Failed to extract entities',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/appointments', methods=['GET'])
@limiter.limit("30 per minute")
def get_available_appointments():
    """
    Get available appointment slots
    """
    try:
        # Extract query parameters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        appointment_type = request.args.get('type')
        provider = request.args.get('provider')

        # Get available appointments
        appointments = appointment_bot.get_available_appointments(
            date_from=date_from,
            date_to=date_to,
            appointment_type=appointment_type,
            provider=provider
        )

        return jsonify({
            'appointments': appointments,
            'count': len(appointments),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Error getting available appointments", error=str(e))
        return jsonify({
            'error': 'Failed to get available appointments',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/appointments', methods=['POST'])
@limiter.limit("20 per minute")
def book_appointment():
    """
    Book a new appointment
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['date', 'time', 'appointment_type', 'user_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Missing required field: {field}',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

        # Book the appointment
        appointment = appointment_bot.book_appointment(
            user_id=data['user_id'],
            date=data['date'],
            time=data['time'],
            appointment_type=data['appointment_type'],
            provider=data.get('provider'),
            notes=data.get('notes'),
            special_requirements=data.get('special_requirements')
        )

        return jsonify({
            'appointment': appointment,
            'message': 'Appointment booked successfully',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Error booking appointment", error=str(e))
        return jsonify({
            'error': 'Failed to book appointment',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/conversation/<session_id>', methods=['GET'])
@limiter.limit("60 per minute")
def get_conversation_history(session_id):
    """
    Get conversation history for a session
    """
    try:
        # Validate session ID
        if not validate_session(session_id):
            return jsonify({
                'error': 'Invalid session ID',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        # Get conversation history
        history = conversation_manager.get_conversation_history(session_id)

        return jsonify({
            'session_id': session_id,
            'history': history,
            'count': len(history),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Error getting conversation history", error=str(e), session_id=session_id)
        return jsonify({
            'error': 'Failed to get conversation history',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/conversation/<session_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
def clear_conversation_history(session_id):
    """
    Clear conversation history for a session
    """
    try:
        # Validate session ID
        if not validate_session(session_id):
            return jsonify({
                'error': 'Invalid session ID',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        # Clear conversation history
        conversation_manager.clear_conversation_history(session_id)

        return jsonify({
            'message': 'Conversation history cleared',
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Error clearing conversation history", error=str(e), session_id=session_id)
        return jsonify({
            'error': 'Failed to clear conversation history',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Load environment variables at the top
from dotenv import load_dotenv
load_dotenv()

if __name__ == '__main__':

    # Get configuration
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5001))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    logger.info("Starting Flask application", host=host, port=port, debug=debug)

    # Run the application
    app.run(host=host, port=port, debug=debug, threaded=True)
