import re
import json
from typing import Dict, List, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)

class IntentClassifier:
    def __init__(self, llm=None):
        self.llm = llm
        self.is_ready_flag = True

    def is_ready(self) -> bool:
        """Check if the classifier is ready"""
        return self.is_ready_flag

    def classify(self, message: str, context: Dict = None) -> Dict[str, any]:
        """Classify user intent from message using LLM"""
        try:
            # Use LLM for intent classification
            if self.llm:
                prompt = f"""
                Analyze this user message and classify their intent. The user is interacting with a dental appointment booking chatbot.

                Message: "{message}"

                Context: {context.get('conversation_state', 'none') if context else 'none'}

                Classify the intent as one of these categories:
                1. book_appointment - User wants to schedule/book a new appointment
                2. reschedule_appointment - User wants to change/move an existing appointment
                3. cancel_appointment - User wants to cancel an appointment
                4. check_appointments - User wants to view their appointments
                5. general_inquiry - General questions about hours, location, contact info, etc.

                Consider the conversation context. If the user is in the middle of booking and provides details like dates, times, or names, classify as book_appointment.

                Respond with JSON format:
                {{
                    "intent": "intent_name",
                    "confidence": 0.0-1.0,
                    "reasoning": "brief explanation"
                }}
                """

                try:
                    response = self.llm.predict(prompt)

                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        return {
                            'intent': result.get('intent', 'general_inquiry'),
                            'confidence': float(result.get('confidence', 0.7)),
                            'alternatives': []
                        }
                except Exception as e:
                    logger.warning(f"LLM intent classification failed: {e}")

            # Fallback to rule-based if LLM fails
            message_lower = message.lower()

            if 'reschedule' in message_lower or 'change my appointment' in message_lower:
                return {'intent': 'reschedule_appointment', 'confidence': 0.9, 'alternatives': []}
            elif 'previous bookings' in message_lower or 'my bookings' in message_lower:
                return {'intent': 'check_appointments', 'confidence': 0.9, 'alternatives': []}
            elif 'cancel' in message_lower:
                return {'intent': 'cancel_appointment', 'confidence': 0.9, 'alternatives': []}
            elif 'book' in message_lower and 'appointment' in message_lower:
                return {'intent': 'book_appointment', 'confidence': 0.8, 'alternatives': []}
            else:
                return {'intent': 'general_inquiry', 'confidence': 0.3, 'alternatives': []}

        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            return {
                'intent': 'general_inquiry',
                'confidence': 0.0,
                'alternatives': []
            }
