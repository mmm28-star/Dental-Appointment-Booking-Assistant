import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class EntityExtractor:
    def __init__(self, llm=None):
        self.llm = llm
        self.is_ready_flag = True

    def is_ready(self) -> bool:
        """Check if the extractor is ready"""
        return self.is_ready_flag

    def extract(self, message: str) -> Dict[str, Any]:
        """Extract entities from user message using LLM"""
        try:
            # Use LLM for entity extraction
            if self.llm:
                from datetime import datetime
                current_date = datetime.now().strftime('%Y-%m-%d')
                current_year = datetime.now().year

                prompt = f"""
                Extract relevant entities from this user message for a dental appointment booking system.

                Message: "{message}"
                Current date: {current_date}
                Current year: {current_year}

                Extract the following entities if present:
                - name: Person's full name (first and last name)
                - appointment_type: Type of appointment (consultation, cleaning, treatment, follow-up, emergency, orthodontic, cosmetic, checkup, exam, therapy, session, meeting, massage, haircut, service)
                - date: Appointment date in YYYY-MM-DD format
                - time: Appointment time in HH:MM format (24-hour)
                - doctor: Doctor's name (Dr. Sarah Johnson, Dr. Michael Chen, Dr. Emily Rodriguez, Dr. James Wilson, Dr. Lisa Thompson)
                - phone: Phone number
                - email: Email address

                For dates, convert relative terms:
                - "today" -> current date ({current_date})
                - "tomorrow" -> next day
                - "next week" -> 7 days from now
                - "Monday", "Tuesday", etc. -> next occurrence of that day
                - "27th", "28th", etc. -> current month and year ({current_year})
                - "28 october", "28th october" -> {current_year}-10-28 (use {current_year} if year not specified)

                For times, convert to 24-hour format:
                - "4pm" -> "16:00"
                - "2:30pm" -> "14:30"
                - "morning" -> "09:00"
                - "afternoon" -> "14:00"
                - "evening" -> "18:00"

                Respond with JSON format:
                {{
                    "name": "extracted name or null",
                    "appointment_type": "extracted type or null",
                    "date": "YYYY-MM-DD or null",
                    "time": "HH:MM or null",
                    "doctor": "doctor name or null",
                    "phone": "phone number or null",
                    "email": "email address or null"
                }}
                """

                try:
                    response = self.llm.predict(prompt)

                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        # Filter out null values
                        entities = {k: v for k, v in result.items() if v is not None and v != "null"}
                        logger.info(f"LLM entities extracted", entities=entities)
                        return entities
                except Exception as e:
                    logger.warning(f"LLM entity extraction failed: {e}")

            # Fallback to rule-based extraction
            message_lower = message.lower()
            entities = {}

            # Extract appointment type
            appointment_type = self._extract_appointment_type(message_lower)
            if appointment_type:
                entities['appointment_type'] = appointment_type

            # Extract date
            date = self._extract_date(message_lower)
            if date:
                entities['date'] = date

            # Extract time
            time = self._extract_time(message_lower)
            if time:
                entities['time'] = time

            # Extract provider/doctor
            provider = self._extract_provider(message_lower)
            if provider:
                entities['doctor'] = provider

            # Extract phone number
            phone = self._extract_phone(message)
            if phone:
                entities['phone'] = phone

            # Extract email
            email = self._extract_email(message)
            if email:
                entities['email'] = email

            # Extract name
            name = self._extract_name(message)
            if name:
                entities['name'] = name

            logger.info(f"Rule-based entities extracted", entities=entities)
            return entities

        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {}

    def _extract_appointment_type(self, message: str) -> str:
        """Extract appointment type from message"""
        for appt_type in self.appointment_types:
            if appt_type in message:
                return appt_type.replace(' ', '_')
        return None

    def _extract_date(self, message: str) -> str:
        """Extract date from message"""
        # Look for common date patterns
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
            r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)',  # 28 october
        ]

        for pattern in date_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                        year, month, day = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    elif 'january|february|march|april|may|june|july|august|september|october|november|december' in pattern:  # 28 october
                        day, month_name = match.groups()
                        month_num = {
                            'january': 1, 'february': 2, 'march': 3, 'april': 4,
                            'may': 5, 'june': 6, 'july': 7, 'august': 8,
                            'september': 9, 'october': 10, 'november': 11, 'december': 12
                        }[month_name.lower()]
                        # Assume current year
                        current_year = datetime.now().year
                        date_obj = datetime(current_year, month_num, int(day))
                    else:  # MM/DD/YYYY or MM-DD-YYYY
                        month, day, year = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))

                    # Validate date
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue

        # Look for relative dates
        if 'today' in message:
            return datetime.now().strftime('%Y-%m-%d')
        elif 'tomorrow' in message:
            return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in message:
            return (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d')

        # Look for ordinal dates (27th, 28th, etc.)
        ordinal_pattern = r'(\d{1,2})(st|nd|rd|th)'
        ordinal_match = re.search(ordinal_pattern, message)
        if ordinal_match:
            day = int(ordinal_match.group(1))
            if 1 <= day <= 31:
                # Assume current month and year
                today = datetime.now()
                try:
                    target_date = datetime(today.year, today.month, day)
                    # If the date has passed this month, assume next month
                    if target_date < today:
                        if today.month == 12:
                            target_date = datetime(today.year + 1, 1, day)
                        else:
                            target_date = datetime(today.year, today.month + 1, day)
                    return target_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass  # Invalid date, continue to other patterns

        # Look for day names (Monday, Tuesday, etc.)
        day_names = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }

        for day_name, day_num in day_names.items():
            if day_name in message:
                # Find the next occurrence of this day
                today = datetime.now()
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')

        return None

    def _extract_time(self, message: str) -> str:
        """Extract time from message"""
        # Look for time patterns
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',  # HH:MM AM/PM
            r'(\d{1,2})\s*(am|pm)',  # H AM/PM
        ]

        for pattern in time_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    if ':' in match.group(0):
                        hour, minute = match.groups()[:2]
                        ampm = match.groups()[2] if len(match.groups()) > 2 else None
                    else:
                        hour = match.groups()[0]
                        minute = '00'
                        ampm = match.groups()[1]

                    hour = int(hour)
                    minute = int(minute)

                    # Convert to 24-hour format
                    if ampm and ampm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif ampm and ampm.lower() == 'am' and hour == 12:
                        hour = 0

                    return f"{hour:02d}:{minute:02d}"
                except ValueError:
                    continue

        return None

    def _extract_provider(self, message: str) -> str:
        """Extract provider from message"""
        for provider in self.providers:
            if provider in message:
                return provider.title()

        # Handle variations like "Dr sarah", "dr sarah", etc.
        if 'dr sarah' in message or 'dr. sarah' in message:
            return 'Dr. Sarah Johnson'
        elif 'dr michael' in message or 'dr. michael' in message:
            return 'Dr. Michael Chen'
        elif 'dr emily' in message or 'dr. emily' in message:
            return 'Dr. Emily Rodriguez'
        elif 'dr james' in message or 'dr. james' in message:
            return 'Dr. James Wilson'
        elif 'dr lisa' in message or 'dr. lisa' in message:
            return 'Dr. Lisa Thompson'

        return None

    def _extract_phone(self, message: str) -> str:
        """Extract phone number from message"""
        phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
        match = re.search(phone_pattern, message)
        return match.group(1) if match else None

    def _extract_email(self, message: str) -> str:
        """Extract email from message"""
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        match = re.search(email_pattern, message)
        return match.group(1) if match else None

    def _extract_name(self, message: str) -> str:
        """Extract name from message"""
        # Don't extract names if the message is about selecting a doctor
        if re.search(r'\b(dr\.?|doctor)\b', message, re.IGNORECASE):
            return None

        # Look for patterns like "My name is John Smith" or "I am John Smith"
        name_patterns = [
            r'(?:my name is|i am|i\'m|name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Two capitalized words
            r'([A-Z][a-z]+)'  # Single capitalized word (but filter out common words)
        ]

        for pattern in name_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                # Filter out common words that aren't names
                common_words = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                               'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                               'September', 'October', 'November', 'December', 'Dr', 'Doctor', 'My', 'I', 'Am', 'Is'}

                for match in matches:
                    if match not in common_words and len(match.split()) >= 1:
                        return match

        return None
