const express = require('express');
const { body, param, query } = require('express-validator');
const { authenticate, optionalAuth } = require('../middleware/auth');
const { validateRequest } = require('../middleware/validateRequest');
const { generateChatbotToken, sendMessage, getChatHistory } = require('../controllers/chatbotController');
const logger = require('../utils/logger');

const router = express.Router();

/**
 * @route   POST /api/chatbot/token
 * @desc    Generate short-lived access token for chatbot
 * @access  Public (with optional authentication)
 */
router.post('/token',
  [
    body('sessionId').optional().isUUID().withMessage('Session ID must be a valid UUID'),
    body('language').optional().isLength({ min: 2, max: 10 }).withMessage('Language must be 2-10 characters'),
    body('userAgent').optional().isLength({ max: 500 }).withMessage('User agent too long'),
    body('ipAddress').optional().isIP().withMessage('Invalid IP address')
  ],
  validateRequest,
  optionalAuth,
  async (req, res) => {
    try {
      const { sessionId, language = 'en', userAgent, ipAddress } = req.body;
      const userId = req.user?.id || null;

      logger.info('Generating chatbot token', {
        userId,
        sessionId,
        language,
        ip: req.ip
      });

      const result = await generateChatbotToken({
        userId,
        sessionId,
        language,
        userAgent: userAgent || req.get('User-Agent'),
        ipAddress: ipAddress || req.ip
      });

      res.status(200).json({
        success: true,
        data: result,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error generating chatbot token:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Failed to generate chatbot token',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   POST /api/chatbot/message
 * @desc    Send message to chatbot and get response
 * @access  Public (with optional authentication)
 */
router.post('/message',
  [
    body('message').notEmpty().isLength({ min: 1, max: 1000 }).withMessage('Message is required and must be 1-1000 characters'),
    body('sessionToken').notEmpty().isLength({ min: 10, max: 255 }).withMessage('Session token is required'),
    body('messageType').optional().isIn(['user', 'system']).withMessage('Message type must be user or system'),
    body('metadata').optional().isObject().withMessage('Metadata must be an object')
  ],
  validateRequest,
  optionalAuth,
  async (req, res) => {
    try {
      const { message, sessionToken, messageType = 'user', metadata = {} } = req.body;
      const userId = req.user?.id || null;

      logger.info('Processing chatbot message', {
        userId,
        sessionToken,
        messageType,
        messageLength: message.length,
        ip: req.ip
      });

      const result = await sendMessage({
        message,
        sessionToken,
        messageType,
        userId,
        metadata,
        userAgent: req.get('User-Agent'),
        ipAddress: req.ip
      });

      res.status(200).json({
        success: true,
        data: result,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error processing chatbot message:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Failed to process message',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   GET /api/chatbot/history/:sessionId
 * @desc    Get chat history for a session
 * @access  Private (requires authentication)
 */
router.get('/history/:sessionId',
  [
    param('sessionId').isUUID().withMessage('Session ID must be a valid UUID'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('offset').optional().isInt({ min: 0 }).withMessage('Offset must be a non-negative integer')
  ],
  validateRequest,
  authenticate,
  async (req, res) => {
    try {
      const { sessionId } = req.params;
      const { limit = 50, offset = 0 } = req.query;
      const userId = req.user.id;

      logger.info('Retrieving chat history', {
        userId,
        sessionId,
        limit,
        offset
      });

      const result = await getChatHistory({
        sessionId,
        userId,
        limit: parseInt(limit),
        offset: parseInt(offset)
      });

      res.status(200).json({
        success: true,
        data: result,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error retrieving chat history:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Failed to retrieve chat history',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   GET /api/chatbot/sessions
 * @desc    Get user's chat sessions
 * @access  Private (requires authentication)
 */
router.get('/sessions',
  [
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('offset').optional().isInt({ min: 0 }).withMessage('Offset must be a non-negative integer'),
    query('status').optional().isIn(['active', 'completed', 'expired']).withMessage('Status must be active, completed, or expired')
  ],
  validateRequest,
  authenticate,
  async (req, res) => {
    try {
      const { limit = 20, offset = 0, status } = req.query;
      const userId = req.user.id;

      logger.info('Retrieving user chat sessions', {
        userId,
        limit,
        offset,
        status
      });

      const result = await getUserChatSessions({
        userId,
        limit: parseInt(limit),
        offset: parseInt(offset),
        status
      });

      res.status(200).json({
        success: true,
        data: result,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error retrieving chat sessions:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Failed to retrieve chat sessions',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   POST /api/chatbot/sessions/:sessionId/end
 * @desc    End a chat session
 * @access  Private (requires authentication)
 */
router.post('/sessions/:sessionId/end',
  [
    param('sessionId').isUUID().withMessage('Session ID must be a valid UUID')
  ],
  validateRequest,
  authenticate,
  async (req, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user.id;

      logger.info('Ending chat session', {
        userId,
        sessionId
      });

      const result = await endChatSession({
        sessionId,
        userId
      });

      res.status(200).json({
        success: true,
        data: result,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error ending chat session:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Failed to end chat session',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

module.exports = router;
