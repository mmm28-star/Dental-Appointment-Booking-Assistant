const { query } = require('../utils/database');
const logger = require('../utils/logger');

const createChatSession = async (sessionData) => {
  try {
    const { userId, sessionToken, language, userAgent, ipAddress } = sessionData;

    const result = await query(
      `INSERT INTO chat_sessions (user_id, session_token, language, user_agent, ip_address, status)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [userId, sessionToken, language, userAgent, ipAddress, 'active']
    );

    logger.info('Chat session created', { sessionId: result.rows[0].id });
    return result.rows[0];
  } catch (error) {
    logger.error('Error creating chat session:', error);
    throw error;
  }
};

const getChatSessionByToken = async (sessionToken) => {
  try {
    const result = await query(
      'SELECT * FROM chat_sessions WHERE session_token = $1',
      [sessionToken]
    );

    return result.rows[0] || null;
  } catch (error) {
    logger.error('Error getting chat session by token:', error);
    throw error;
  }
};

const updateChatSession = async (sessionId, updateData) => {
  try {
    const fields = [];
    const values = [];
    let paramCount = 1;

    Object.keys(updateData).forEach(key => {
      if (updateData[key] !== undefined) {
        fields.push(`${key} = $${paramCount}`);
        values.push(updateData[key]);
        paramCount++;
      }
    });

    if (fields.length === 0) {
      throw new Error('No fields to update');
    }

    values.push(sessionId);
    const result = await query(
      `UPDATE chat_sessions SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP
       WHERE id = $${paramCount}
       RETURNING *`,
      values
    );

    return result.rows[0];
  } catch (error) {
    logger.error('Error updating chat session:', error);
    throw error;
  }
};

const createChatMessage = async (messageData) => {
  try {
    const { sessionId, messageType, content, intent, entities, confidenceScore, processingTimeMs } = messageData;

    const result = await query(
      `INSERT INTO chat_messages (session_id, message_type, content, intent, entities, confidence_score, processing_time_ms)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING *`,
      [sessionId, messageType, content, intent, JSON.stringify(entities), confidenceScore, processingTimeMs]
    );

    logger.info('Chat message created', { messageId: result.rows[0].id });
    return result.rows[0];
  } catch (error) {
    logger.error('Error creating chat message:', error);
    throw error;
  }
};

const getChatMessagesBySession = async (sessionId, limit = 50, offset = 0) => {
  try {
    const result = await query(
      `SELECT * FROM chat_messages
       WHERE session_id = $1
       ORDER BY created_at ASC
       LIMIT $2 OFFSET $3`,
      [sessionId, limit, offset]
    );

    return result.rows;
  } catch (error) {
    logger.error('Error getting chat messages:', error);
    throw error;
  }
};

const getUserChatSessions = async ({ userId, limit = 20, offset = 0, status }) => {
  try {
    let queryText = 'SELECT * FROM chat_sessions WHERE user_id = $1';
    const values = [userId];
    let paramCount = 1;

    if (status) {
      paramCount++;
      queryText += ` AND status = $${paramCount}`;
      values.push(status);
    }

    paramCount++;
    queryText += ` ORDER BY created_at DESC LIMIT $${paramCount}`;
    values.push(limit);

    paramCount++;
    queryText += ` OFFSET $${paramCount}`;
    values.push(offset);

    const result = await query(queryText, values);
    return result.rows;
  } catch (error) {
    logger.error('Error getting user chat sessions:', error);
    throw error;
  }
};

const endChatSession = async (sessionId) => {
  try {
    const result = await query(
      `UPDATE chat_sessions
       SET status = 'completed', ended_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
       WHERE id = $1
       RETURNING *`,
      [sessionId]
    );

    logger.info('Chat session ended', { sessionId });
    return result.rows[0];
  } catch (error) {
    logger.error('Error ending chat session:', error);
    throw error;
  }
};

module.exports = {
  createChatSession,
  getChatSessionByToken,
  updateChatSession,
  createChatMessage,
  getChatMessagesBySession,
  getUserChatSessions,
  endChatSession
};
