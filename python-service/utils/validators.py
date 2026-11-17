import re
import uuid
from typing import Any, Dict

def validate_request(data: Dict[str, Any]) -> bool:
    """Validate incoming request data"""
    if not isinstance(data, dict):
        return False

    # Check for required fields based on endpoint
    if 'message' in data:
        if not isinstance(data['message'], str) or len(data['message'].strip()) == 0:
            return False

    return True

def validate_session(session_id: str) -> bool:
    """Validate session ID format"""
    if not session_id:
        return False

    # Check if it's a valid UUID
    try:
        uuid.UUID(session_id)
        return True
    except ValueError:
        return False

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
    return re.match(pattern, phone) is not None
