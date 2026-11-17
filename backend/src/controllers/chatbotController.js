const { v4: uuidv4 } = require('uuid');
const axios = require('axios');
const logger = require('../utils/logger');
const {
  createChatSession,
  getChatSessionByToken,
  updateChatSession,
  createChatMessage,
  getChatMessagesBySession,
  getUserChatSessions,
  endChatSession
} = require('../models/ChatSession');

/**
 * Generate short-lived access token for chatbot
 * @param {Object} params - Parameters for token generation
 * @returns {Object} - Token and session information
 */
const generateChatbotToken = async (params) => {
  try {
    const { userId, sessionId, language, userAgent, ipAddress } = params;

    // Generate session token
    const sessionToken = `sess_${uuidv4().replace(/-/g, '')}`;

    // Create chat session
    const session = await createChatSession({
      userId,
      sessionToken,
      language,
      userAgent,
      ipAddress
    });

    logger.info('Chatbot token generated', {
      sessionId: session.id,
      sessionToken,
      userId,
      language
    });

    return {
      sessionToken,
      sessionId: session.id,
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
      language: session.language
    };
  } catch (error) {
    logger.error('Error generating chatbot token:', error);
    throw new Error('Failed to generate chatbot token');
  }
};

/**
 * Send message to chatbot and get response
 * @param {Object} params - Message parameters
 * @returns {Object} - Response from chatbot
 */
const sendMessage = async (params) => {
  try {
    const { message, sessionToken, messageType, userId, metadata, userAgent, ipAddress } = params;

    // Get chat session
    const session = await getChatSessionByToken(sessionToken);
    if (!session) {
      throw new Error('Invalid session token');
    }

    if (session.status !== 'active') {
      throw new Error('Session is not active');
    }

    // Create user message record
    const userMessage = await createChatMessage({
      sessionId: session.id,
      messageType: 'user',
      content: message,
      metadata
    });

    logger.info('User message created', {
      messageId: userMessage.id,
      sessionId: session.id,
      messageLength: message.length
    });

    // Send message to Python microservice
    const startTime = Date.now();
    let response;

    try {
      const pythonServiceUrl = process.env.PYTHON_SERVICE_URL || 'http://localhost:5001';
      const response = await axios.post(`${pythonServiceUrl}/chat`, {
        message,
        sessionId: session.id,
        userId,
        language: session.language,
        metadata
      }, {
        timeout: parseInt(process.env.PYTHON_SERVICE_TIMEOUT) || 30000,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': userAgent
        }
      });

      const processingTime = Date.now() - startTime;

      // Create assistant message record
      const assistantMessage = await createChatMessage({
        sessionId: session.id,
        messageType: 'assistant',
        content: response.data.response,
        intent: response.data.intent,
        entities: response.data.entities,
        confidenceScore: response.data.confidence,
        processingTimeMs: processingTime
      });

      // Update session with new intent if provided
      if (response.data.intent) {
        await updateChatSession(session.id, {
          intent: response.data.intent
        });
      }

      logger.info('Chatbot response processed', {
        messageId: assistantMessage.id,
        sessionId: session.id,
        intent: response.data.intent,
        confidence: response.data.confidence,
        processingTime
      });

      return {
        response: response.data.response,
        intent: response.data.intent,
        entities: response.data.entities,
        confidence: response.data.confidence,
        sessionId: session.id,
        messageId: assistantMessage.id,
        processingTime
      };
    } catch (pythonError) {
      logger.error('Python service error:', pythonError);

      // Fallback response
      const fallbackResponse = "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.";

      const assistantMessage = await createChatMessage({
        sessionId: session.id,
        messageType: 'assistant',
        content: fallbackResponse,
        processingTimeMs: Date.now() - startTime
      });

      return {
        response: fallbackResponse,
        intent: 'error',
        entities: null,
        confidence: 0.0,
        sessionId: session.id,
        messageId: assistantMessage.id,
        processingTime: Date.now() - startTime,
        error: 'Service temporarily unavailable'
      };
    }
  } catch (error) {
    logger.error('Error processing chatbot message:', error);
    throw new Error('Failed to process message');
  }
};

/**
 * Get chat history for a session
 * @param {Object} params - Parameters for retrieving chat history
 * @returns {Object} - Chat history data
 */
const getChatHistory = async (params) => {
  try {
    const { sessionId, userId, limit, offset } = params;

    // Verify session belongs to user
    const session = await getChatSessionByToken(sessionId);
    if (!session || (session.userId && session.userId !== userId)) {
      throw new Error('Session not found or access denied');
    }

    // Get chat messages
    const messages = await getChatMessagesBySession(sessionId, limit, offset);

    logger.info('Chat history retrieved', {
      sessionId,
      userId,
      messageCount: messages.length,
      limit,
      offset
    });

    return {
      sessionId,
      messages,
      totalCount: messages.length,
      hasMore: messages.length === limit
    };
  } catch (error) {
    logger.error('Error retrieving chat history:', error);
    throw new Error('Failed to retrieve chat history');
  }
};

/**
 * Get user's chat sessions
 * @param {Object} params - Parameters for retrieving sessions
 * @returns {Object} - User's chat sessions
 */
const getUserChatSessionsController = async (params) => {
  try {
    const { userId, limit, offset, status } = params;

    const sessions = await getUserChatSessions({
      userId,
      limit,
      offset,
      status
    });

    logger.info('User chat sessions retrieved', {
      userId,
      sessionCount: sessions.length,
      limit,
      offset,
      status
    });

    return {
      sessions,
      totalCount: sessions.length,
      hasMore: sessions.length === limit
    };
  } catch (error) {
    logger.error('Error retrieving user chat sessions:', error);
    throw new Error('Failed to retrieve chat sessions');
  }
};

/**
 * End a chat session
 * @param {Object} params - Parameters for ending session
 * @returns {Object} - Session end confirmation
 */
const endChatSessionController = async (params) => {
  try {
    const { sessionId, userId } = params;

    // Verify session belongs to user
    const session = await getChatSessionByToken(sessionId);
    if (!session || (session.userId && session.userId !== userId)) {
      throw new Error('Session not found or access denied');
    }

    // End the session
    await endChatSession(sessionId);

    logger.info('Chat session ended', {
      sessionId,
      userId
    });

    return {
      sessionId,
      status: 'ended',
      endedAt: new Date().toISOString()
    };
  } catch (error) {
    logger.error('Error ending chat session:', error);
    throw new Error('Failed to end chat session');
  }
};

module.exports = {
  generateChatbotToken,
  sendMessage,
  getChatHistory,
  getUserChatSessions: getUserChatSessionsController,
  endChatSession: endChatSessionController
};
