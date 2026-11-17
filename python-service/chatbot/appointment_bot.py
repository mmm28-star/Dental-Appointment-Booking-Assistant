"""
Appointment Booking Chatbot using LangChain
Main chatbot class that handles conversation flow and appointment scheduling
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import uuid

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain

from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .conversation_manager import ConversationManager
from utils.database import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

class AppointmentBot:
    """
    Main chatbot class for appointment booking using LangChain
    """

    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor,
                 conversation_manager: ConversationManager, db_manager: DatabaseManager):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor
        self.conversation_manager = conversation_manager
        self.db_manager = db_manager

        # Initialize LangChain with OpenAI
        try:
            from langchain_openai import ChatOpenAI
            from langchain.memory import ConversationBufferWindowMemory
            from langchain.chains import ConversationChain
            from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

            # Initialize OpenAI LLM
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7,
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )

            # Initialize conversation memory
            self.memory = ConversationBufferWindowMemory(
                k=10,  # Keep last 10 exchanges
                return_messages=True,
                memory_key="history"
            )

            # Create conversation chain
            self.conversation_chain = ConversationChain(
                llm=self.llm,
                memory=self.memory,
                verbose=True
            )

            logger.info("LangChain with OpenAI initialized successfully")
        except Exception as e:
            logger.warning(f"LangChain not available, using rule-based responses: {e}")
            self.llm = None
            self.memory = None
            self.conversation_chain = None

        # Appointment booking states
        self.booking_states = {
            'greeting': 'greeting',
            'intent_classification': 'intent_classification',
            'appointment_details': 'appointment_details',
            'date_selection': 'date_selection',
            'time_selection': 'time_selection',
            'confirmation': 'confirmation',
            'booking_complete': 'booking_complete'
        }

        # Available appointment types
        self.appointment_types = {
            'consultation': 'Initial consultation and examination',
            'cleaning': 'Regular cleaning and checkup',
            'treatment': 'Specific treatment or procedure',
            'follow_up': 'Follow-up appointment after treatment',
            'emergency': 'Emergency care',
            'orthodontic': 'Orthodontic consultation or adjustment',
            'cosmetic': 'Cosmetic procedures'
        }

        # Available providers
        self.providers = [
            'Dr. Sarah Johnson',
            'Dr. Michael Chen',
            'Dr. Emily Rodriguez',
            'Dr. James Wilson',
            'Dr. Lisa Thompson'
        ]

    def _create_conversation_chain(self):  # -> ConversationChain:
        """Create the conversation chain with system prompt"""

        system_prompt = """You are an AI assistant for an appointment booking system.
        Your role is to help patients schedule, reschedule, or cancel appointments in a friendly and professional manner.

        IMPORTANT CONVERSATION FLOW:
        1. ALWAYS collect the patient's FULL NAME first before proceeding with any appointment booking
        2. Then collect appointment type, date, and time in that order
        3. Confirm all details before booking
        4. Maintain context throughout the conversation

        Key responsibilities:
        1. Greet patients warmly and understand their needs
        2. ALWAYS ask for full name first when booking appointments
        3. Help them choose appropriate appointment types
        4. Find available dates and times
        5. Collect necessary information (name, contact, insurance, etc.)
        6. Confirm appointment details before booking
        7. Handle rescheduling and cancellations
        8. Answer general questions about the clinic

        Available appointment types:
        - consultation: Initial consultation and examination (60 minutes)
        - cleaning: Regular cleaning and checkup (45 minutes)
        - treatment: Specific treatment or procedure (90 minutes)
        - follow_up: Follow-up appointment after treatment (30 minutes)
        - emergency: Emergency care (60 minutes)
        - orthodontic: Orthodontic consultation or adjustment (45 minutes)
        - cosmetic: Cosmetic procedures (120 minutes)

        Available providers:
        - Dr. Sarah Johnson (General Dentistry)
        - Dr. Michael Chen (Orthodontics)
        - Dr. Emily Rodriguez (Periodontics)
        - Dr. James Wilson (Oral Surgery)
        - Dr. Lisa Thompson (Pediatric Dentistry)

        Office hours: Monday-Friday 8:00 AM - 6:00 PM, Saturday 9:00 AM - 2:00 PM
        Location: 123 Main Street, Dental City, DC 12345
        Phone: (555) 123-4567

        CONVERSATION CONTEXT:
        - Remember the patient's name throughout the conversation
        - Maintain appointment booking state
        - Track collected information (name, type, date, time)
        - Provide personalized responses using the patient's name

        Keep responses brief and to the point. Be helpful but concise."""

        if not self.llm or not self.memory:
            return None

        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        return ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=prompt,
            verbose=False
        )

    def process_message(self, message: str, session_id: str, user_id: Optional[str] = None,
                       language: str = 'en', metadata: Dict = None) -> Dict[str, Any]:
        """
        Process a user message and generate appropriate response

        Args:
            message: User's message
            session_id: Unique session identifier
            user_id: User ID if authenticated
            language: Language preference
            metadata: Additional metadata

        Returns:
            Dictionary containing response, intent, entities, and confidence
        """
        try:
            logger.info(f"Processing message for session {session_id}",
                       message_length=len(message), user_id=user_id)

            # Get conversation context first
            context = self.conversation_manager.get_context(session_id)
            logger.info(f"Retrieved context for session {session_id}", context=context)
            logger.info(f"Conversation state: {context.get('conversation_state', 'none')}")

            # Classify intent
            intent_result = self.intent_classifier.classify(message, context)
            intent = intent_result['intent']
            confidence = intent_result['confidence']

            # Extract entities
            entities = self.entity_extractor.extract(message)

            # Check if we're in an appointment inquiry flow FIRST
            if context.get('conversation_state') == 'checking_appointments':
                logger.info(f"Handling appointment inquiry for session {session_id} with entities: {entities}")
                try:
                    response = self._handle_appointment_inquiry(message, session_id, user_id, entities, context)
                    # Update conversation state from response
                    if response.get('conversation_state'):
                        self.conversation_manager.update_context(session_id, {
                            'conversation_state': response.get('conversation_state')
                        })
                    # Store conversation before returning
                    self.conversation_manager.add_exchange(
                        session_id, 'user', message, intent, entities, confidence
                    )
                    self.conversation_manager.add_exchange(
                        session_id, 'assistant', response['response'], intent, entities, confidence
                    )
                    return response
                except Exception as e:
                    logger.error(f"Error in appointment inquiry: {e}")
                    return {
                        'response': "I'm sorry, I'm having trouble accessing your appointments right now. Please try again.",
                        'intent': intent,
                        'entities': entities,
                        'confidence': confidence,
                        'metadata': {'error': str(e)}
                    }
            # Check if we're in a cancellation flow (regardless of intent)
            elif context.get('conversation_state') == 'cancelling_appointments':
                logger.info(f"Handling appointment cancellation for session {session_id} with entities: {entities}, intent: {intent}")
                response = self._handle_cancellation(message, session_id, user_id, entities, context)
                # Always return early for cancellation to prevent LangChain override
                # Store conversation before returning
                self.conversation_manager.add_exchange(
                    session_id, 'user', message, intent, entities, confidence
                )
                self.conversation_manager.add_exchange(
                    session_id, 'assistant', response['response'], intent, entities, confidence
                )
                return response
            # Check if we're in a rescheduling flow
            elif context.get('conversation_state') == 'rescheduling_appointments':
                logger.info(f"Handling appointment rescheduling for session {session_id} with entities: {entities}")
                response = self._handle_reschedule(message, session_id, user_id, entities, context)
                # Always return early for rescheduling to prevent LangChain override
                # Store conversation before returning
                self.conversation_manager.add_exchange(
                    session_id, 'user', message, intent, entities, confidence
                )
                self.conversation_manager.add_exchange(
                    session_id, 'assistant', response['response'], intent, entities, confidence
                )
                return response
            # Check if we're in a booking flow - maintain context (but not if we're cancelling or rescheduling)
            elif (context.get('conversation_state') in ['awaiting_name', 'awaiting_appointment_type', 'awaiting_date', 'awaiting_time', 'awaiting_doctor', 'appointment_details'] and
                  context.get('conversation_state') not in ['cancelling_appointments', 'rescheduling_appointments']):
                response = self._handle_appointment_booking(message, session_id, user_id, entities, context)
            # Check if we have accumulated entities and are continuing a booking (but not if we're checking appointments, cancelling, or rescheduling)
            elif (context.get('accumulated_entities') and len(context.get('accumulated_entities', {})) > 0 and
                  intent in ['book_appointment', 'general_inquiry'] and
                  context.get('conversation_state') not in ['checking_appointments', 'cancelling_appointments', 'rescheduling_appointments']):
                response = self._handle_appointment_booking(message, session_id, user_id, entities, context)
            # Check if we're in a booking flow and have entities but missing name (but not if we're cancelling or rescheduling)
            elif ((context.get('accumulated_entities', {}).get('appointment_type') or
                  context.get('accumulated_entities', {}).get('date') or
                  context.get('accumulated_entities', {}).get('time')) and intent in ['book_appointment', 'general_inquiry'] and
                  context.get('conversation_state') not in ['cancelling_appointments', 'rescheduling_appointments']):
                response = self._handle_appointment_booking(message, session_id, user_id, entities, context)
            # Check if we have entities that suggest we're in a booking flow (but not if we're cancelling or rescheduling)
            elif ((entities.get('name') or entities.get('date') or entities.get('time') or entities.get('doctor') or entities.get('appointment_type')) and
                  intent in ['book_appointment', 'general_inquiry'] and
                  context.get('conversation_state') not in ['cancelling_appointments', 'rescheduling_appointments']):
                response = self._handle_appointment_booking(message, session_id, user_id, entities, context)
            # Check if we have enough information to complete a booking (but not if we're cancelling or rescheduling)
            elif ((context.get('accumulated_entities', {}).get('name') and
                  context.get('accumulated_entities', {}).get('appointment_type') and
                  context.get('accumulated_entities', {}).get('date') and
                  context.get('accumulated_entities', {}).get('time')) and intent in ['book_appointment', 'general_inquiry'] and
                  context.get('conversation_state') not in ['cancelling_appointments', 'rescheduling_appointments']):
                response = self._handle_appointment_booking(message, session_id, user_id, entities, context)
            # Check if we're continuing a booking from previous messages
            elif (context.get('accumulated_entities', {}).get('appointment_type') or
                  context.get('accumulated_entities', {}).get('date') or
                  context.get('accumulated_entities', {}).get('time')) and intent in ['book_appointment', 'general_inquiry']:
                response = self._handle_appointment_booking(message, session_id, user_id, entities, context)
            # Process based on intent
            elif intent == 'book_appointment':
                response = self._handle_appointment_booking_llm(message, session_id, user_id, entities, context)
            elif intent == 'reschedule_appointment':
                # Set conversation state for rescheduling
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'rescheduling_appointments'
                })
                response = self._handle_reschedule(message, session_id, user_id, entities, context)
            elif intent == 'cancel_appointment':
                # Set conversation state for cancellation
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'cancelling_appointments'
                })
                response = self._handle_cancellation(message, session_id, user_id, entities, context)
            elif intent == 'check_appointments':
                # Set conversation state for appointment inquiry
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'checking_appointments'
                })
                # Update the context so it's available in the method
                context = self.conversation_manager.get_context(session_id)
                response = self._handle_appointment_inquiry_llm(message, session_id, user_id, entities, context)
                # Always return early for appointment inquiry to prevent LangChain override
                # Store conversation before returning
                self.conversation_manager.add_exchange(
                    session_id, 'user', message, intent, entities, confidence
                )
                self.conversation_manager.add_exchange(
                    session_id, 'assistant', response['response'], intent, entities, confidence
                )
                return response
            elif intent == 'general_inquiry':
                response = self._handle_general_inquiry(message, session_id, user_id, entities, context)
            else:
                response = self._handle_unknown_intent(message, session_id, user_id, entities, context)

            # Enhance response with LangChain if available
            # AI Enhancement for all responses to make them more natural
            # But preserve structured responses for booking flows
            if self.conversation_chain and not response.get('metadata', {}).get('appointment') and not response.get('metadata', {}).get('structured_response') and not response.get('metadata', {}).get('appointments'):
                try:
                    # Create context-aware prompt for LangChain
                    context_info = ""
                    if context.get('conversation_state'):
                        context_info += f"Current booking state: {context.get('conversation_state')}. "
                    if context.get('accumulated_entities'):
                        context_info += f"Available entities: {context.get('accumulated_entities')}. "

                    # Use LangChain with context
                    enhanced_message = f"You are a helpful appointment booking assistant. The user said: '{message}'. {context_info}Please respond naturally while maintaining the booking flow. Keep it friendly and professional. You can handle any type of appointment - medical, dental, business, personal, etc."

                    ai_response = self.conversation_chain.predict(input=enhanced_message)

                    if ai_response and len(ai_response.strip()) > 0:
                        response['response'] = ai_response.strip()
                        logger.info(f"LangChain-enhanced response generated for session {session_id}")

                except Exception as e:
                    logger.warning(f"LangChain enhancement failed, using rule-based response: {e}")

            # Store conversation
            self.conversation_manager.add_exchange(
                session_id, 'user', message, intent, entities, confidence
            )
            self.conversation_manager.add_exchange(
                session_id, 'assistant', response['response'], intent, entities, confidence
            )

            # Update context - accumulate entities from the conversation
            accumulated_entities = context.get('accumulated_entities', {}).copy()

            # Only update entities that don't overwrite important user information
            for key, value in entities.items():
                if key == 'name' and accumulated_entities.get('name'):
                    # Don't overwrite user's name with doctor's name
                    if not any(doc_name.lower() in value.lower() for doc_name in ['dr', 'doctor']):
                        accumulated_entities[key] = value
                    # Keep the original user name if the new name looks like a doctor
                    else:
                        logger.info(f"Preserving user name '{accumulated_entities[key]}' instead of overwriting with '{value}'")
                else:
                    accumulated_entities[key] = value


            # Preserve conversation state if it's set in the response, otherwise keep the current state
            # Special handling for cancellation and rescheduling states
            if context.get('conversation_state') in ['cancelling_appointments', 'rescheduling_appointments']:
                new_conversation_state = response.get('conversation_state', context.get('conversation_state'))
            else:
                new_conversation_state = response.get('conversation_state', context.get('conversation_state', 'active'))

            self.conversation_manager.update_context(session_id, {
                'last_intent': intent,
                'last_entities': entities,
                'accumulated_entities': accumulated_entities,
                'conversation_state': new_conversation_state
            })

            logger.info(f"Generated response for session {session_id}",
                       intent=intent, confidence=confidence,
                       response_length=len(response['response']))

            return {
                'response': response['response'],
                'intent': intent,
                'entities': entities,
                'confidence': confidence,
                'metadata': response.get('metadata', {}),
                'state': response.get('state', 'active')
            }

        except Exception as e:
            logger.error(f"Error processing message for session {session_id}", error=str(e))
            return {
                'response': "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.",
                'intent': 'error',
                'entities': {},
                'confidence': 0.0,
                'metadata': {'error': str(e)},
                'state': 'error'
            }

    def _handle_appointment_booking(self, message: str, session_id: str, user_id: Optional[str],
                                  entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle appointment booking intent"""

        # Merge entities from current message with accumulated entities from conversation
        combined_entities = context.get('accumulated_entities', {}).copy()

        # Add new entities, but preserve user's name if it looks like a doctor name or appointment type
        for key, value in entities.items():
            if key == 'name' and combined_entities.get('name'):
                # Don't overwrite user's name with doctor's name or appointment types
                if (any(doc_name.lower() in value.lower() for doc_name in ['dr', 'doctor']) or
                    value.lower() in ['consultation', 'cleaning', 'treatment', 'follow-up', 'emergency', 'orthodontic', 'cosmetic', 'checkup', 'exam', 'therapy', 'session', 'meeting', 'massage', 'haircut', 'service']):
                    logger.info(f"Preserving user name '{combined_entities[key]}' instead of overwriting with '{value}'")
                    continue
            combined_entities[key] = value

            logger.info(f"Context merging debug",
                   current_entities=entities,
                   accumulated_entities=context.get('accumulated_entities', {}),
                   combined_entities=combined_entities,
                   conversation_state=context.get('conversation_state', 'none'))

        # Check if we have all required information
        required_info = ['name', 'appointment_type', 'date', 'time', 'doctor']
        missing_info = [info for info in required_info if info not in combined_entities]

        logger.info(f"Checking booking requirements - combined_entities: {combined_entities}, missing_info: {missing_info}")
        logger.info(f"Required info check: name={combined_entities.get('name')}, appointment_type={combined_entities.get('appointment_type')}, date={combined_entities.get('date')}, time={combined_entities.get('time')}, doctor={combined_entities.get('doctor')}")

        if missing_info:
            # Ask for missing information in order
            if 'name' not in combined_entities:
                response = "What's your name?"
                # Update conversation state
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'awaiting_name',
                    'accumulated_entities': combined_entities
                })
                return {
                    'response': response,
                    'metadata': {'missing_info': missing_info},
                    'state': 'awaiting_name'
                }
            elif 'appointment_type' not in combined_entities:
                response = f"What type of appointment? (consultation, cleaning, treatment, etc.)"
                # Update conversation state
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'awaiting_appointment_type',
                    'accumulated_entities': combined_entities
                })
                return {
                    'response': response,
                    'metadata': {'missing_info': missing_info},
                    'state': 'awaiting_appointment_type'
                }
            elif 'date' not in combined_entities:
                response = f"When would you like to schedule it?"
                # Update conversation state
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'awaiting_date',
                    'accumulated_entities': combined_entities
                })
                return {
                    'response': response,
                    'metadata': {'missing_info': missing_info},
                    'state': 'awaiting_date'
                }
            elif 'time' not in combined_entities:
                response = f"What time on {combined_entities.get('date', 'that day')}?"
                # Update conversation state
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'awaiting_time',
                    'accumulated_entities': combined_entities
                })
                return {
                    'response': response,
                    'metadata': {'missing_info': missing_info},
                    'state': 'awaiting_time'
                }
            elif 'doctor' not in combined_entities:
                # Show available doctors
                doctors = self._get_available_doctors()
                doctor_list = "\n".join([f"• {doc['name']} - {doc['specialization']}" for doc in doctors])
                response = f"Which doctor?\n\n{doctor_list}"
                # Update conversation state
                self.conversation_manager.update_context(session_id, {
                    'conversation_state': 'awaiting_doctor',
                    'accumulated_entities': combined_entities
                })
                return {
                    'response': response,
                    'metadata': {'doctors': doctors, 'missing_info': missing_info},
                    'state': 'awaiting_doctor'
                }
            else:
                response = "I need a bit more information to book your appointment. Could you please specify your name, appointment type, date, time, and preferred doctor?"
                return {
                    'response': response,
                    'metadata': {'missing_info': missing_info},
                    'state': 'awaiting_info'
                }
        else:
            # Try to book the appointment
            logger.info(f"All required info present, attempting to book appointment",
                       combined_entities=combined_entities,
                       user_id=user_id)
            try:
                appointment = self._book_appointment(user_id, combined_entities, context)
                # Enhanced appointment confirmation with doctor details
                doctor_info = self._get_doctor_info(combined_entities['doctor'])
                response = f"""Perfect! I've successfully booked your appointment. Here are the details:

📅 **Appointment Details:**
• **Patient:** {combined_entities['name']}
• **Type:** {combined_entities['appointment_type'].title()}
• **Date:** {combined_entities['date']}
• **Time:** {combined_entities['time']}
• **Doctor:** {appointment['provider']}
• **Specialization:** {doctor_info.get('specialization', 'General Dentistry')}
• **Email:** {doctor_info.get('email', 'N/A')}
• **Phone:** {doctor_info.get('phone', 'N/A')}

You'll receive a confirmation email shortly with all the details. Is there anything else I can help you with?"""
                return {
                    'response': response,
                    'metadata': {'appointment': appointment},
                    'state': 'booking_complete'
                }
            except Exception as e:
                response = f"I'm sorry, I couldn't book that appointment. {str(e)} Would you like to try a different date or time?"

        return {
            'response': response,
            'metadata': {'missing_info': missing_info},
            'state': 'appointment_details'
        }

    def _handle_reschedule(self, message: str, session_id: str, user_id: Optional[str],
                         entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle appointment rescheduling"""

        # Get accumulated entities from context
        accumulated_entities = context.get('accumulated_entities', {})
        combined_entities = {**accumulated_entities, **entities}

        # Update accumulated entities with new entities
        updated_accumulated = {**accumulated_entities, **entities}
        self.conversation_manager.update_context(session_id, {
            'accumulated_entities': updated_accumulated
        })

        # Check if we have a name to look up appointments
        if 'name' not in combined_entities:
            # Update conversation state for rescheduling
            self.conversation_manager.update_context(session_id, {
                'conversation_state': 'rescheduling_appointments'
            })
            return {
                'response': "I'd be happy to help you reschedule an appointment! First, could you please provide your name so I can look up your appointments?",
                'conversation_state': 'rescheduling_appointments',
                'intent': 'reschedule_appointment',
                'entities': entities,
                'confidence': 0.9
            }

        # Look up appointments by name
        try:
            appointments = self._get_appointments_by_name(combined_entities['name'])

            if not appointments:
                return {
                    'response': f"I don't see any upcoming appointments for {combined_entities['name']}. Would you like to book a new appointment instead?",
                    'state': 'no_appointments',
                    'intent': 'reschedule_appointment',
                    'entities': entities,
                    'confidence': 0.9
                }

            # If user provided new date/time details, try to reschedule it
            new_date = entities.get('date') or context.get('accumulated_entities', {}).get('new_date')
            new_time = entities.get('time') or context.get('accumulated_entities', {}).get('new_time')

            if new_date or new_time:
                # Find matching appointment (use the first one if multiple)
                matching_appointment = appointments[0] if appointments else None

                if matching_appointment:
                    # Update the appointment with new details
                    success = self._update_appointment(
                        matching_appointment['id'],
                        new_date=new_date,
                        new_time=new_time
                    )

                    if success:
                        return {
                            'response': f" I've successfully rescheduled your {matching_appointment['appointment_type']} appointment with {matching_appointment['provider_name']} to {new_date} at {new_time}. You'll receive a confirmation email shortly.",
                            'state': 'rescheduling_complete',
                            'intent': 'reschedule_appointment',
                            'entities': entities,
                            'confidence': 0.9
                        }
                    else:
                        return {
                            'response': "I'm sorry, I couldn't reschedule that appointment. Please contact our office directly.",
                            'state': 'rescheduling_failed',
                            'intent': 'reschedule_appointment',
                            'entities': entities,
                            'confidence': 0.9
                        }

            # Show available appointments for rescheduling
            appointment_list = "\n".join([
                f"• **{apt['appointment_type'].title()}** with {apt['provider_name']} on {apt['appointment_date']} at {apt['appointment_time']} (Status: {apt['status']})"
                for apt in appointments
            ])

            return {
                'response': f"I found {len(appointments)} upcoming appointment(s) for {combined_entities['name']}:\n\n{appointment_list}\n\nWhich appointment would you like to reschedule? Please let me know the appointment type or date, and I'll help you find a new time.",
                'metadata': {'appointments': appointments},
                'conversation_state': 'rescheduling_appointments',
                'intent': 'reschedule_appointment',
                'entities': entities,
                'confidence': 0.9
            }

        except Exception as e:
            logger.error(f"Error looking up appointments for rescheduling: {e}")
            return {
                'response': "I'm sorry, I'm having trouble accessing your appointments right now. Please try again or contact our office directly.",
                'state': 'error',
                'intent': 'reschedule_appointment',
                'entities': entities,
                'confidence': 0.9
            }

    def _handle_cancellation(self, message: str, session_id: str, user_id: Optional[str],
                           entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle appointment cancellation"""

        # Get accumulated entities from context
        accumulated_entities = context.get('accumulated_entities', {})
        combined_entities = {**accumulated_entities, **entities}

        logger.info(f"Cancellation handler - message: {message}, entities: {entities}, combined_entities: {combined_entities}")

        # Check if we have a name to look up appointments
        if 'name' not in combined_entities:
            # Update conversation state for cancellation
            self.conversation_manager.update_context(session_id, {
                'conversation_state': 'cancelling_appointments'
            })
            return {
                'response': "I'd be happy to help you cancel your appointment! First, could you please provide your name so I can look up your appointments?",
                'conversation_state': 'cancelling_appointments',
                'metadata': {'structured_response': True},
                'intent': 'cancel_appointment',
                'entities': entities,
                'confidence': 0.9
            }

        # Look up appointments by name
        try:
            appointments = self._get_appointments_by_name(combined_entities['name'])

            if not appointments:
                return {
                    'response': f"I don't see any upcoming appointments for {combined_entities['name']}. Would you like to book a new appointment instead?",
                    'state': 'no_appointments',
                    'intent': 'cancel_appointment',
                    'entities': entities,
                    'confidence': 0.9
                }

            # If user provided specific appointment details, try to cancel it
            if entities.get('appointment_type') or entities.get('date') or entities.get('time'):
                logger.info(f"Looking for matching appointments with entities: {entities}")
                # Find matching appointments
                matching_appointments = []
                for apt in appointments:
                    logger.info(f"Checking appointment: {apt['appointment_type']} vs {entities.get('appointment_type')}")
                    if (entities.get('appointment_type') and entities.get('appointment_type').lower() in apt['appointment_type'].lower()) or \
                       (entities.get('date') and entities.get('date') in apt['appointment_date']) or \
                       (entities.get('time') and entities.get('time') in apt['appointment_time']):
                        matching_appointments.append(apt)
                        logger.info(f"Found matching appointment: {apt['id']}")

                logger.info(f"Found {len(matching_appointments)} matching appointments")

                if matching_appointments:
                    # If multiple appointments match, cancel the first one
                    if len(matching_appointments) > 1:
                        # Cancel all matching appointments
                        cancelled_count = 0
                        for apt in matching_appointments:
                            success = self._cancel_appointment(apt['id'])
                            if success:
                                cancelled_count += 1

                        if cancelled_count > 0:
                            return {
                                'response': f" I've successfully cancelled {cancelled_count} {entities.get('appointment_type', 'appointment')} appointment(s). You'll receive a confirmation email shortly.",
                                'state': 'cancellation_complete',
                                'intent': 'cancel_appointment',
                                'entities': entities,
                                'confidence': 0.9
                            }
                        else:
                            return {
                                'response': "I'm sorry, I couldn't cancel those appointments. Please contact our office directly.",
                                'state': 'cancellation_failed',
                                'intent': 'cancel_appointment',
                                'entities': entities,
                                'confidence': 0.9
                            }
                    else:
                        # Cancel the single matching appointment
                        matching_appointment = matching_appointments[0]
                        success = self._cancel_appointment(matching_appointment['id'])
                        if success:
                            return {
                                'response': f" I've successfully cancelled your {matching_appointment['appointment_type']} appointment with {matching_appointment['provider_name']} on {matching_appointment['appointment_date']} at {matching_appointment['appointment_time']}. You'll receive a confirmation email shortly.",
                                'state': 'cancellation_complete',
                                'intent': 'cancel_appointment',
                                'entities': entities,
                                'confidence': 0.9
                            }
                        else:
                            return {
                                'response': "I'm sorry, I couldn't cancel that appointment. Please contact our office directly.",
                                'state': 'cancellation_failed',
                                'intent': 'cancel_appointment',
                                'entities': entities,
                                'confidence': 0.9
                            }

            # Show available appointments for cancellation
            appointment_list = "\n".join([
                f"• **{apt['appointment_type'].title()}** with {apt['provider_name']} on {apt['appointment_date']} at {apt['appointment_time']} (Status: {apt['status']})"
                for apt in appointments
            ])

            return {
                'response': f"I found {len(appointments)} upcoming appointment(s) for {combined_entities['name']}:\n\n{appointment_list}\n\nWhich appointment would you like to cancel? Please let me know the appointment type or date, and I'll cancel it for you.",
                'metadata': {'appointments': appointments},
                'conversation_state': 'cancelling_appointments',
                'intent': 'cancel_appointment',
                'entities': entities,
                'confidence': 0.9
            }

        except Exception as e:
            logger.error(f"Error looking up appointments for cancellation: {e}")
            return {
                'response': "I'm sorry, I'm having trouble accessing your appointments right now. Please try again or contact our office directly.",
                'state': 'error',
                'intent': 'cancel_appointment',
                'entities': entities,
                'confidence': 0.9
            }

    def _handle_name_provided(self, message: str, session_id: str, user_id: Optional[str],
                             entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle when user provides their name after being asked"""
        try:
            from utils.database import DatabaseManager
            db = DatabaseManager()

            # Extract name from the message
            name = message.strip()

            # Search for user by name with flexible matching
            # Split the name into parts for more flexible searching
            name_parts = name.strip().split()

            if len(name_parts) == 1:
                # Single name - search first name or last name
                user_query = """
                SELECT id, first_name, last_name, email, phone
                FROM users
                WHERE (first_name ILIKE :name OR last_name ILIKE :name)
                """
                users = db.execute_query(user_query, {'name': f"%{name_parts[0]}%"})
            else:
                # Multiple names - try different combinations
                first_name = name_parts[0]
                last_name = name_parts[-1]
                full_name = " ".join(name_parts)

                user_query = """
                SELECT id, first_name, last_name, email, phone
                FROM users
                WHERE (first_name ILIKE :first_name AND last_name ILIKE :last_name)
                   OR (first_name ILIKE :full_name OR last_name ILIKE :full_name)
                   OR CONCAT(first_name, ' ', last_name) ILIKE :full_name
                   OR CONCAT(last_name, ' ', first_name) ILIKE :full_name
                """
                users = db.execute_query(user_query, {
                    'first_name': f"%{first_name}%",
                    'last_name': f"%{last_name}%",
                    'full_name': f"%{full_name}%"
                })

            if not users:
                # Try to find users with similar names or check if they have appointments
                # Look for users with appointments that might match
                appointment_query = """
                SELECT DISTINCT u.id, u.first_name, u.last_name, u.email, u.phone, a.created_at
                FROM users u
                JOIN appointments a ON u.id = a.user_id
                WHERE (u.first_name ILIKE :name OR u.last_name ILIKE :name
                       OR CONCAT(u.first_name, ' ', u.last_name) ILIKE :name)
                ORDER BY a.created_at DESC
                LIMIT 1
                """
                users = db.execute_query(appointment_query, {'name': f"%{name}%"})

                if not users:
                    return {
                        'response': f"I couldn't find an account for '{name}'. Please check the spelling or try providing your full name (first and last name).",
                        'state': 'awaiting_name'
                    }

            # Get appointments for the found user
            user_id = users[0][0]
            appointments_query = """
            SELECT id, appointment_type, appointment_date, appointment_time,
                   provider_name, status, location, notes
            FROM appointments
            WHERE user_id = :user_id
            ORDER BY appointment_date, appointment_time
            """

            appointments = db.execute_query(appointments_query, {'user_id': user_id})

            if not appointments:
                return {
                    'response': f"Hello {users[0][1]}! I found your account but don't see any upcoming appointments. Would you like to book one?",
                    'state': 'no_appointments'
                }

            # Convert database rows to dictionaries
            appointments_list = []
            for apt in appointments:
                appointments_list.append({
                    'id': str(apt[0]),
                    'type': apt[1],
                    'date': str(apt[2]),
                    'time': str(apt[3]),
                    'provider': apt[4],
                    'status': apt[5],
                    'location': apt[6],
                    'notes': apt[7]
                })

            # Format appointments
            appointment_list = "\n".join([
                f"• {apt['type'].title()} with {apt['provider']} on {apt['date']} at {apt['time']} (Status: {apt['status']})"
                for apt in appointments_list
            ])

            return {
                'response': f"Hello {users[0][1]}! Here are your appointments:\n\n{appointment_list}\n\nIs there anything specific you'd like to know about these appointments?",
                'metadata': {'appointments': appointments_list},
                'state': 'appointments_listed'
            }

        except Exception as e:
            logger.error(f"Error in name lookup: {e}")
            return {
                'response': "I'm having trouble accessing your account right now. Please try again or contact our office directly.",
                'state': 'error'
            }

    def _handle_appointment_inquiry(self, message: str, session_id: str, user_id: Optional[str],
                                   entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle appointment inquiry"""

        try:
            # First try to use entities from the entity extractor
            user_info = {
                "name": entities.get('name'),
                "phone": entities.get('phone'),
                "email": entities.get('email')
            }

            # If no entities found, try using OpenAI to extract user information from the message
            if not any(user_info.values()) and self.llm:
                # Create a prompt to extract user information
                extraction_prompt = f"""
                Extract user information from this message: "{message}"

                Look for:
                - Name (first name, last name, or full name)
                - Phone number
                - Email address
                - Any other identifying information

                Return as JSON format:
                {{
                    "name": "extracted name or null",
                    "phone": "extracted phone or null",
                    "email": "extracted email or null"
                }}
                """

                try:
                    extraction_response = self.llm.predict(extraction_prompt)
                    # Parse the response to extract user info
                    import json
                    import re

                    # Try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', extraction_response, re.DOTALL)
                    if json_match:
                        user_info = json.loads(json_match.group())
                    else:
                        user_info = {"name": None, "phone": None, "email": None}
                except:
                    user_info = {"name": None, "phone": None, "email": None}

            # Query database for appointments
            from utils.database import DatabaseManager
            db = DatabaseManager()

            # Check if we have any user information to search with
            if not user_info.get('name') and not user_info.get('email') and not user_info.get('phone'):
                # If no user information extracted, ask for name
                # Keep conversation state as 'checking_appointments'
                return {
                    'response': "I'd be happy to help you check your appointments! Could you please provide your full name so I can look up your account?",
                    'state': 'awaiting_name',
                    'intent': 'check_appointments',
                    'entities': entities,
                    'confidence': 0.9
                }

            # Try to find user by extracted information
            user_query = """
            SELECT id, first_name, last_name, email, phone
            FROM users
            WHERE 1=1
            """
            params = {}

            if user_info.get('name'):
                user_query += " AND (first_name ILIKE :name OR last_name ILIKE :name OR CONCAT(first_name, ' ', last_name) ILIKE :name)"
                params['name'] = f"%{user_info['name']}%"
            elif user_info.get('email'):
                user_query += " AND email ILIKE :email"
                params['email'] = f"%{user_info['email']}%"
            elif user_info.get('phone'):
                user_query += " AND phone ILIKE :phone"
                params['phone'] = f"%{user_info['phone']}%"

            users = db.execute_query(user_query, params)

            if not users:
                # If no specific user found, ask for name to search
                return {
                    'response': "I couldn't find an account with that information. Could you please provide your full name so I can look up your account?",
                    'state': 'awaiting_name',
                    'intent': 'check_appointments',
                    'entities': entities,
                    'confidence': 0.9
                }

            # Get appointments for the found user(s)
            user_id = users[0][0]  # Get the first user's ID
            appointments_query = """
            SELECT id, appointment_type, appointment_date, appointment_time,
                   provider_name, status, location, notes
            FROM appointments
            WHERE user_id = :user_id
            ORDER BY appointment_date, appointment_time
            """

            appointments = db.execute_query(appointments_query, {'user_id': user_id})

            if not appointments:
                return {
                    'response': f"I found your account but don't see any upcoming appointments. Would you like to book one?",
                    'state': 'no_appointments',
                    'intent': 'check_appointments',
                    'entities': entities,
                    'confidence': 0.9
                }

            # Convert database rows to dictionaries for JSON serialization
            appointments_list = []
            for apt in appointments:
                appointments_list.append({
                    'id': str(apt[0]),
                    'type': apt[1],
                    'date': str(apt[2]),
                    'time': str(apt[3]),
                    'provider': apt[4],
                    'status': apt[5],
                    'location': apt[6],
                    'notes': apt[7]
                })

            # Format appointments
            appointment_list = "\n".join([
                f"• {apt['type'].title()} with {apt['provider']} on {apt['date']} at {apt['time']} (Status: {apt['status']})"
                for apt in appointments_list
            ])

            return {
                'response': f"Here are your upcoming appointments:\n\n{appointment_list}\n\nIs there anything specific you'd like to know about these appointments?",
                'metadata': {'appointments': appointments_list},
                'state': 'appointments_listed',
                'intent': 'check_appointments',
                'entities': entities,
                'confidence': 0.9
            }

        except Exception as e:
            logger.error(f"Error in appointment inquiry: {e}")
            # Fallback to sample data
            sample_appointments = [
                {
                    'id': '1',
                    'type': 'consultation',
                    'date': '2024-01-15',
                    'time': '09:00:00',
                    'provider': 'Dr. Sarah Johnson',
                    'status': 'confirmed'
                }
            ]

            return {
                'response': f"I'm having trouble accessing the database right now. Here are some sample appointments:\n\n• Consultation with Dr. Sarah Johnson on 2024-01-15 at 09:00:00 (Status: confirmed)\n\nPlease try again or contact our office directly.",
                'metadata': {'appointments': sample_appointments},
                'state': 'appointments_listed',
                'intent': 'check_appointments',
                'entities': entities,
                'confidence': 0.9
            }

    def _handle_general_inquiry(self, message: str, session_id: str, user_id: Optional[str],
                               entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle general inquiries"""

        # Use the conversation chain for general inquiries
        if self.llm:
            response = self.conversation_chain.predict(input=message)
        else:
            # Mock response for demo
            response = "I'm an appointment booking assistant. I can help you book appointments, check your schedule, or answer questions about our services. How can I help you today?"

        return {
            'response': response,
            'state': 'general_inquiry'
        }

    def _handle_unknown_intent(self, message: str, session_id: str, user_id: Optional[str],
                              entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle unknown or unclear intents"""

        return {
            'response': "I'm not sure I understand. Could you please clarify what you'd like to do? I can help you book, reschedule, or cancel appointments, or answer questions about our services.",
            'state': 'clarification_needed'
        }

    def _book_appointment(self, user_id: Optional[str], entities: Dict, context: Dict) -> Dict[str, Any]:
        """Book a new appointment"""

        try:
            from utils.database import DatabaseManager
            import uuid
            from datetime import datetime

            db = DatabaseManager()
            appointment_id = str(uuid.uuid4())

            # If no user_id provided or user_id is not a valid UUID, try to find or create user
            if not user_id or not self._is_valid_uuid(user_id):
                # Extract user info from context or entities
                user_name = entities.get('name', 'Unknown User')
                user_email = entities.get('email', f'user_{appointment_id}@example.com')
                user_phone = entities.get('phone', '000-000-0000')

                logger.info(f"Booking appointment with user info",
                           user_name=user_name,
                           user_email=user_email,
                           user_phone=user_phone,
                           entities=entities)

                # Try to find existing user by exact name match only
                name_parts = user_name.split(' ', 1)
                first_name = name_parts[0] if name_parts else 'Unknown'
                last_name = name_parts[1] if len(name_parts) > 1 else 'User'

                # Only search by exact name match to avoid false positives
                user_query = """
                SELECT id FROM users
                WHERE first_name = :first_name AND last_name = :last_name
                """

                logger.info(f"Searching for user with exact match", first_name=first_name, last_name=last_name)
                existing_users = db.execute_query(user_query, {
                    'first_name': first_name,
                    'last_name': last_name
                })
                logger.info(f"User search results", existing_users=existing_users)

                if existing_users:
                    user_id = existing_users[0][0]
                    logger.info(f"Found existing user", user_id=user_id, user_name=user_name)
                else:
                    # Create new user
                    user_id = str(uuid.uuid4())
                    create_user_query = """
                    INSERT INTO users (id, email, password_hash, first_name, last_name, phone, is_verified, created_at, updated_at)
                    VALUES (:id, :email, :password_hash, :first_name, :last_name, :phone, :is_verified, :created_at, :updated_at)
                    """

                    # Execute user creation query
                    from sqlalchemy import text
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(create_user_query), {
                                'id': user_id,
                                'email': user_email,
                                'password_hash': 'temp_password_hash',  # Temporary password for chatbot users
                                'first_name': first_name,
                                'last_name': last_name,
                                'phone': user_phone,
                                'is_verified': True,
                                'created_at': datetime.utcnow(),
                                'updated_at': datetime.utcnow()
                            })
                            conn.commit()
                        logger.info(f"Created new user successfully", user_id=user_id, user_name=user_name, email=user_email)
                    except Exception as e:
                        logger.error(f"Failed to create new user: {e}", user_name=user_name, email=user_email)
                        # If user creation fails, we should still proceed with the appointment
                        # but we need to handle this case properly
                        raise Exception(f"Failed to create user account: {str(e)}")

            # Insert appointment into database
            appointment_query = """
            INSERT INTO appointments (id, user_id, appointment_type, appointment_date, appointment_time,
                                   provider_name, provider_email, status, location, notes, created_at, updated_at)
            VALUES (:id, :user_id, :appointment_type, :appointment_date, :appointment_time,
                   :provider_name, :provider_email, :status, :location, :notes, :created_at, :updated_at)
            """

            provider_name = entities.get('doctor', entities.get('provider', 'Dr. Sarah Johnson'))
            provider_email = f"{provider_name.lower().replace(' ', '.')}@dentalclinic.com"

            # Execute appointment insertion query
            from sqlalchemy import text
            logger.info(f"Attempting to insert appointment",
                       appointment_id=appointment_id,
                       user_id=user_id,
                       entities=entities)

            with db.engine.connect() as conn:
                result = conn.execute(text(appointment_query), {
                    'id': appointment_id,
                    'user_id': user_id,
                    'appointment_type': entities['appointment_type'],
                    'appointment_date': entities['date'],
                    'appointment_time': entities['time'],
                    'provider_name': provider_name,
                    'provider_email': provider_email,
                    'status': 'confirmed',
                    'location': 'Main Office - Room 101',
                    'notes': f"Appointment booked via chatbot",
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                conn.commit()
                logger.info(f"Appointment insertion result", result=result)

            logger.info(f"Appointment booked successfully", appointment_id=appointment_id, user_id=user_id)

            return {
                'id': appointment_id,
                'type': entities['appointment_type'],
                'date': entities['date'],
                'time': entities['time'],
                'provider': provider_name,
                'status': 'confirmed',
                'created_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error booking appointment: {e}",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        entities=entities,
                        user_id=user_id)
            raise Exception(f"Failed to book appointment: {str(e)}")

    def _get_user_appointments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's appointments from database"""

        # This would query the database
        # For now, return mock data
        return [
            {
                'id': 'apt_123',
                'type': 'cleaning',
                'date': '2024-01-20',
                'time': '10:00',
                'provider': 'Dr. Sarah Johnson',
                'status': 'confirmed'
            }
        ]

    def _reschedule_appointment(self, appointment_id: str, entities: Dict) -> Dict[str, Any]:
        """Reschedule an existing appointment"""

        # This would update the database
        return {
            'id': appointment_id,
            'new_date': entities['date'],
            'new_time': entities['time'],
            'status': 'rescheduled'
        }


    def get_available_appointments(self, date_from: Optional[str] = None,
                                 date_to: Optional[str] = None,
                                 appointment_type: Optional[str] = None,
                                 provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available appointment slots"""

        # This would query the database for available slots
        # For now, return mock data
        return [
            {
                'date': '2024-01-20',
                'time': '09:00',
                'provider': 'Dr. Sarah Johnson',
                'type': 'consultation',
                'available': True
            },
            {
                'date': '2024-01-20',
                'time': '10:00',
                'provider': 'Dr. Sarah Johnson',
                'type': 'consultation',
                'available': True
            }
        ]

    def is_openai_available(self) -> bool:
        """Check if OpenAI API is available"""
        return self.llm is not None

    def is_langchain_available(self) -> bool:
        """Check if LangChain is available"""
        return self.conversation_chain is not None

    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if a string is a valid UUID"""
        try:
            import uuid
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

    def _get_available_doctors(self) -> List[Dict[str, Any]]:
        """Get list of available doctors from database"""
        try:
            from utils.database import DatabaseManager
            db = DatabaseManager()

            query = """
            SELECT name, email, phone, specialization
            FROM providers
            WHERE is_active = true
            ORDER BY name
            """

            result = db.execute_query(query)
            doctors = []

            for row in result:
                doctors.append({
                    'name': row[0],
                    'email': row[1],
                    'phone': row[2],
                    'specialization': row[3]
                })

            return doctors

        except Exception as e:
            logger.error(f"Error getting available doctors: {e}")
            # Return default doctors if database fails
            return [
                {'name': 'Dr. Sarah Johnson', 'email': 'sarah.johnson@dentalclinic.com', 'phone': '+1-555-0101', 'specialization': 'General Dentistry'},
                {'name': 'Dr. Michael Chen', 'email': 'michael.chen@dentalclinic.com', 'phone': '+1-555-0102', 'specialization': 'Orthodontics'},
                {'name': 'Dr. Emily Rodriguez', 'email': 'emily.rodriguez@dentalclinic.com', 'phone': '+1-555-0103', 'specialization': 'Periodontics'},
                {'name': 'Dr. James Wilson', 'email': 'james.wilson@dentalclinic.com', 'phone': '+1-555-0104', 'specialization': 'Oral Surgery'},
                {'name': 'Dr. Lisa Thompson', 'email': 'lisa.thompson@dentalclinic.com', 'phone': '+1-555-0105', 'specialization': 'Pediatric Dentistry'}
            ]

    def _get_doctor_info(self, doctor_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific doctor"""
        try:
            from utils.database import DatabaseManager
            db = DatabaseManager()

            query = """
            SELECT name, email, phone, specialization
            FROM providers
            WHERE name ILIKE :doctor_name AND is_active = true
            """

            result = db.execute_query(query, {'doctor_name': f'%{doctor_name}%'})

            if result:
                row = result[0]
                return {
                    'name': row[0],
                    'email': row[1],
                    'phone': row[2],
                    'specialization': row[3]
                }
            else:
                # Return default info if not found
                return {
                    'name': doctor_name,
                    'email': 'contact@dentalclinic.com',
                    'phone': '+1-555-0000',
                    'specialization': 'General Dentistry'
                }

        except Exception as e:
            logger.error(f"Error getting doctor info: {e}")
            return {
                'name': doctor_name,
                'email': 'contact@dentalclinic.com',
                'phone': '+1-555-0000',
                'specialization': 'General Dentistry'
            }

    def _get_appointments_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Get appointments for a specific patient by name"""
        try:
            from utils.database import DatabaseManager
            db = DatabaseManager()

            # Search for user by name (flexible matching)
            name_parts = name.strip().split()

            if len(name_parts) == 1:
                # Single name - search first name or last name
                user_query = """
                SELECT id, first_name, last_name
                FROM users
                WHERE (first_name ILIKE :name OR last_name ILIKE :name)
                """
                users = db.execute_query(user_query, {'name': f'%{name_parts[0]}%'})
            else:
                # Multiple names - search for combination
                user_query = """
                SELECT id, first_name, last_name
                FROM users
                WHERE (first_name ILIKE :first_name AND last_name ILIKE :last_name)
                OR (first_name ILIKE :last_name AND last_name ILIKE :first_name)
                """
                users = db.execute_query(user_query, {
                    'first_name': f'%{name_parts[0]}%',
                    'last_name': f'%{name_parts[-1]}%'
                })

            if not users:
                return []

            # Get appointments for all matching users
            user_ids = [str(user[0]) for user in users]
            placeholders = ','.join([f"'{user_id}'" for user_id in user_ids])

            appointment_query = f"""
            SELECT id, appointment_type, appointment_date, appointment_time,
                   provider_name, status, location, notes
            FROM appointments
            WHERE user_id IN ({placeholders})
            AND status IN ('scheduled', 'confirmed')
            ORDER BY appointment_date, appointment_time
            LIMIT 10
            """

            appointments = db.execute_query(appointment_query)

            result = []
            for apt in appointments:
                result.append({
                    'id': str(apt[0]),
                    'appointment_type': apt[1],
                    'appointment_date': str(apt[2]),
                    'appointment_time': str(apt[3]),
                    'provider_name': apt[4],
                    'status': apt[5],
                    'location': apt[6],
                    'notes': apt[7]
                })

            return result

        except Exception as e:
            logger.error(f"Error getting appointments by name: {e}")
            return []

    def _cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel an appointment by ID"""
        try:
            db = DatabaseManager()

            # Update appointment status to cancelled
            update_query = """
            UPDATE appointments
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """

            result = db.execute_query(update_query, [appointment_id])
            logger.info(f"Appointment {appointment_id} cancelled successfully")
            return True

        except Exception as e:
            logger.error(f"Error cancelling appointment {appointment_id}: {e}")
            return False

    def _update_appointment(self, appointment_id: str, new_date: str = None, new_time: str = None,
                          new_appointment_type: str = None) -> bool:
        """Update an appointment with new details"""
        try:
            db = DatabaseManager()

            # Build dynamic update query based on provided parameters
            updates = []
            params = []

            if new_date:
                updates.append("appointment_date = %s")
                params.append(new_date)

            if new_time:
                updates.append("appointment_time = %s")
                params.append(new_time)

            if new_appointment_type:
                updates.append("appointment_type = %s")
                params.append(new_appointment_type)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(appointment_id)

            update_query = f"""
            UPDATE appointments
            SET {', '.join(updates)}
            WHERE id = %s
            """

            # Execute update query directly
            from sqlalchemy import text
            logger.info(f"Updating appointment {appointment_id} with query: {update_query}, params: {params}")
            with db.engine.connect() as conn:
                result = conn.execute(text(update_query), params)
                conn.commit()
                logger.info(f"Update result: {result.rowcount} rows affected")
            logger.info(f"Appointment {appointment_id} updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating appointment {appointment_id}: {e}")
            return False

    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if a string is a valid UUID"""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

    def _handle_appointment_booking_llm(self, message: str, session_id: str, user_id: Optional[str],
                                       entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle appointment booking intent using LLM"""

        try:
            # Use LLM for appointment booking logic
            if self.llm:
                # Get conversation history
                conversation_history = context.get('messages', [])
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])  # Last 5 messages

                prompt = f"""
                You are a dental appointment booking assistant. Help the user book an appointment by gathering the required information and processing their request.

                Current message: "{message}"
                Conversation history: {history_text}
                Current entities: {entities}
                Context: {context}

                Required information for booking:
                - name: Patient's full name
                - appointment_type: Type of appointment (consultation, cleaning, treatment, etc.)
                - date: Appointment date in YYYY-MM-DD format
                - time: Appointment time in HH:MM format
                - doctor: Doctor's name

                Available doctors:
                - Dr. Sarah Johnson (General Dentistry)
                - Dr. Michael Chen (Orthodontics)
                - Dr. Emily Rodriguez (Oral Surgery)
                - Dr. James Wilson (Periodontics)
                - Dr. Lisa Thompson (Cosmetic Dentistry)

                Respond with JSON format:
                {{
                    "action": "ask_for_info|book_appointment|error",
                    "response": "your response to the user",
                    "missing_info": ["list of missing required fields"],
                    "entities": {{"extracted entities from the message"}},
                    "state": "awaiting_name|awaiting_type|awaiting_date|awaiting_time|awaiting_doctor|booking_complete|error"
                }}

                If all required information is available, set action to "book_appointment" and provide a confirmation message.
                If information is missing, set action to "ask_for_info" and ask for the missing information in a friendly way.
                """

                try:
                    response = self.llm.predict(prompt)

                    # Extract JSON from response
                    import json
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())

                        # If booking appointment, actually book it
                        if result.get('action') == 'book_appointment':
                            try:
                                # Merge entities from context and new extraction
                                combined_entities = context.get('accumulated_entities', {}).copy()
                                combined_entities.update(result.get('entities', {}))

                                appointment = self._book_appointment(user_id, combined_entities, context)
                                doctor_info = self._get_doctor_info(combined_entities.get('doctor', 'Dr. Sarah Johnson'))

                                response_text = f"""Perfect! I've successfully booked your appointment. Here are the details:

**Appointment Details:**
• **Patient:** {combined_entities.get('name', 'N/A')}
• **Type:** {combined_entities.get('appointment_type', 'N/A').title()}
• **Date:** {combined_entities.get('date', 'N/A')}
• **Time:** {combined_entities.get('time', 'N/A')}
• **Doctor:** {appointment.get('provider', 'N/A')}
• **Specialization:** {doctor_info.get('specialization', 'General Dentistry')}
• **Email:** {doctor_info.get('email', 'N/A')}
• **Phone:** {doctor_info.get('phone', 'N/A')}

You'll receive a confirmation email shortly with all the details. Is there anything else I can help you with?"""

                                return {
                                    'response': response_text,
                                    'metadata': {'appointment': appointment},
                                    'state': 'booking_complete'
                                }
                            except Exception as e:
                                return {
                                    'response': f"I'm sorry, I couldn't book that appointment. {str(e)} Would you like to try a different date or time?",
                                    'metadata': {'error': str(e)},
                                    'state': 'error'
                                }
                        else:
                            # Ask for missing information
                            missing_info = result.get('missing_info', [])
                            response_text = result.get('response', 'I need more information to book your appointment.')

                            # Update conversation state
                            self.conversation_manager.update_context(session_id, {
                                'conversation_state': result.get('state', 'awaiting_info'),
                                'accumulated_entities': context.get('accumulated_entities', {}).copy()
                            })

                            return {
                                'response': response_text,
                                'metadata': {'missing_info': missing_info},
                                'state': result.get('state', 'awaiting_info')
                            }
                except Exception as e:
                    logger.warning(f"LLM booking logic failed: {e}")

            # Fallback to rule-based logic if LLM fails
            return self._handle_appointment_booking(message, session_id, user_id, entities, context)

        except Exception as e:
            logger.error(f"Error in LLM-based appointment booking: {e}")
            return {
                'response': "I'm sorry, I'm having trouble processing your booking request. Please try again.",
                'metadata': {'error': str(e)},
                'state': 'error'
            }

    def _handle_appointment_inquiry_llm(self, message: str, session_id: str, user_id: Optional[str],
                                       entities: Dict, context: Dict) -> Dict[str, Any]:
        """Handle appointment inquiry using LLM"""

        try:
            # Use LLM for appointment inquiry logic
            if self.llm:
                # Get conversation history
                conversation_history = context.get('messages', [])
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])  # Last 5 messages

                prompt = f"""
                You are a dental appointment booking assistant. Help the user check their appointments by gathering their information and querying the database.

                Current message: "{message}"
                Conversation history: {history_text}
                Current entities: {entities}
                Context: {context}

                To check appointments, you need:
                - name: Patient's full name (required for database lookup)

                If the user provides their name, search the database for their appointments.
                If no name is provided, ask for their full name.

                Respond with JSON format:
                {{
                    "action": "ask_for_name|search_appointments|error",
                    "response": "your response to the user",
                    "user_name": "extracted name if available",
                    "state": "awaiting_name|appointments_found|no_appointments|error"
                }}

                If you have the user's name, set action to "search_appointments" and I will query the database.
                If no name is provided, set action to "ask_for_name" and ask for their full name.
                """

                try:
                    response = self.llm.predict(prompt)

                    # Extract JSON from response
                    import json
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())

                        # If we have a name, search for appointments
                        if result.get('action') == 'search_appointments' and result.get('user_name'):
                            try:
                                from utils.database import DatabaseManager
                                db = DatabaseManager()

                                # Search for user by name with flexible matching
                                name = result.get('user_name')
                                name_parts = name.strip().split()

                                if len(name_parts) == 1:
                                    # Single name - search first name or last name
                                    user_query = """
                                    SELECT id, first_name, last_name, email, phone
                                    FROM users
                                    WHERE (first_name ILIKE :name OR last_name ILIKE :name)
                                    """
                                    users = db.execute_query(user_query, {'name': f"%{name_parts[0]}%"})
                                else:
                                    # Multiple names - try different combinations
                                    first_name = name_parts[0]
                                    last_name = name_parts[-1]
                                    full_name = " ".join(name_parts)

                                    user_query = """
                                    SELECT id, first_name, last_name, email, phone
                                    FROM users
                                    WHERE (first_name ILIKE :first_name AND last_name ILIKE :last_name)
                                       OR (first_name ILIKE :full_name OR last_name ILIKE :full_name)
                                       OR CONCAT(first_name, ' ', last_name) ILIKE :full_name
                                       OR CONCAT(last_name, ' ', first_name) ILIKE :full_name
                                    """
                                    users = db.execute_query(user_query, {
                                        'first_name': f"%{first_name}%",
                                        'last_name': f"%{last_name}%",
                                        'full_name': f"%{full_name}%"
                                    })

                                if not users:
                                    return {
                                        'response': f"I couldn't find an account for '{name}'. Please check the spelling or try providing your full name (first and last name).",
                                        'state': 'awaiting_name',
                                        'intent': 'check_appointments',
                                        'entities': entities,
                                        'confidence': 0.9
                                    }

                                # Get appointments for the found user
                                user_id = users[0][0]
                                appointments_query = """
                                SELECT id, appointment_type, appointment_date, appointment_time,
                                       provider_name, status, location, notes
                                FROM appointments
                                WHERE user_id = :user_id
                                ORDER BY appointment_date, appointment_time
                                """

                                appointments = db.execute_query(appointments_query, {'user_id': user_id})

                                if not appointments:
                                    return {
                                        'response': f"Hello {users[0][1]}! I found your account but don't see any upcoming appointments. Would you like to book one?",
                                        'state': 'no_appointments',
                                        'intent': 'check_appointments',
                                        'entities': entities,
                                        'confidence': 0.9
                                    }

                                # Convert database rows to dictionaries
                                appointments_list = []
                                for apt in appointments:
                                    appointments_list.append({
                                        'id': str(apt[0]),
                                        'type': apt[1],
                                        'date': str(apt[2]),
                                        'time': str(apt[3]),
                                        'provider': apt[4],
                                        'status': apt[5],
                                        'location': apt[6],
                                        'notes': apt[7]
                                    })

                                # Format appointments
                                appointment_list = "\n".join([
                                    f"• {apt['type'].title()} with {apt['provider']} on {apt['date']} at {apt['time']} (Status: {apt['status']})"
                                    for apt in appointments_list
                                ])

                                return {
                                    'response': f"Hello {users[0][1]}! Here are your appointments:\n\n{appointment_list}\n\nIs there anything specific you'd like to know about these appointments?",
                                    'metadata': {'appointments': appointments_list},
                                    'state': 'appointments_listed',
                                    'intent': 'check_appointments',
                                    'entities': entities,
                                    'confidence': 0.9
                                }

                            except Exception as e:
                                logger.error(f"Error in database lookup: {e}")
                                return {
                                    'response': "I'm having trouble accessing your account right now. Please try again or contact our office directly.",
                                    'state': 'error',
                                    'intent': 'check_appointments',
                                    'entities': entities,
                                    'confidence': 0.0
                                }
                        else:
                            # Ask for name
                            return {
                                'response': result.get('response', "I'd be happy to help you check your appointments! Could you please provide your full name so I can look up your account?"),
                                'state': 'awaiting_name',
                                'intent': 'check_appointments',
                                'entities': entities,
                                'confidence': 0.9
                            }
                except Exception as e:
                    logger.warning(f"LLM appointment inquiry failed: {e}")

            # Fallback to rule-based logic if LLM fails
            return self._handle_appointment_inquiry(message, session_id, user_id, entities, context)

        except Exception as e:
            logger.error(f"Error in LLM-based appointment inquiry: {e}")
            return {
                'response': "I'm sorry, I'm having trouble processing your request. Please try again.",
                'metadata': {'error': str(e)},
                'state': 'error'
            }
