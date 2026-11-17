const WebSocket = require('ws');
const logger = require('./logger');

const handleWebSocketConnection = (ws, req) => {
  logger.info('New WebSocket connection', {
    ip: req.socket.remoteAddress,
    userAgent: req.headers['user-agent']
  });

  // Send welcome message
  ws.send(JSON.stringify({
    type: 'welcome',
    message: 'Connected to appointment chatbot',
    timestamp: new Date().toISOString()
  }));

  // Handle incoming messages
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      logger.info('WebSocket message received', { type: data.type });

      // Echo back the message
      ws.send(JSON.stringify({
        type: 'echo',
        originalMessage: data,
        timestamp: new Date().toISOString()
      }));
    } catch (error) {
      logger.error('WebSocket message error:', error);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Invalid message format',
        timestamp: new Date().toISOString()
      }));
    }
  });

  // Handle connection close
  ws.on('close', () => {
    logger.info('WebSocket connection closed');
  });

  // Handle errors
  ws.on('error', (error) => {
    logger.error('WebSocket error:', error);
  });
};

module.exports = { handleWebSocketConnection };
