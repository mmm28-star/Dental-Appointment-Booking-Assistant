from typing import Dict, List, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class ConversationManager:
    def __init__(self):
        self.conversations = {}  # In-memory storage for demo
        self.is_ready_flag = True

    def is_ready(self) -> bool:
        """Check if the conversation manager is ready"""
        return self.is_ready_flag

    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context for a session"""
        return self.conversations.get(session_id, {
            'messages': [],
            'intent_history': [],
            'entities': {},
            'state': 'greeting'
        })

    def add_exchange(self, session_id: str, role: str, content: str,
                    intent: str = None, entities: Dict = None, confidence: float = None):
        """Add a message exchange to the conversation"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'intent_history': [],
                'entities': {},
                'state': 'greeting'
            }

        # Add message
        self.conversations[session_id]['messages'].append({
            'role': role,
            'content': content,
            'timestamp': self._get_timestamp()
        })

        # Add intent to history
        if intent:
            self.conversations[session_id]['intent_history'].append({
                'intent': intent,
                'confidence': confidence,
                'timestamp': self._get_timestamp()
            })

        # Update entities
        if entities:
            self.conversations[session_id]['entities'].update(entities)

        logger.info(f"Exchange added to session {session_id}", role=role, intent=intent)

    def update_context(self, session_id: str, updates: Dict[str, Any]):
        """Update conversation context"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'intent_history': [],
                'entities': {},
                'state': 'greeting'
            }

        self.conversations[session_id].update(updates)
        logger.info(f"Context updated for session {session_id}", updates=updates)
        logger.info(f"Current context for session {session_id}", context=self.conversations[session_id])

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        return self.conversations.get(session_id, {}).get('messages', [])

    def clear_conversation_history(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            self.conversations[session_id]['messages'] = []
            self.conversations[session_id]['intent_history'] = []
            self.conversations[session_id]['entities'] = {}
            self.conversations[session_id]['state'] = 'greeting'
            logger.info(f"Conversation history cleared for session {session_id}")

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
