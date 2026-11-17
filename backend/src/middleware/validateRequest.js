const { validationResult } = require('express-validator');
const logger = require('../utils/logger');

/**
 * Request validation middleware
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next function
 */
const validateRequest = (req, res, next) => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    logger.warn('Validation errors', {
      errors: errors.array(),
      url: req.originalUrl,
      method: req.method,
      ip: req.ip
    });

    return res.status(400).json({
      success: false,
      error: {
        message: 'Validation failed',
        details: errors.array()
      },
      timestamp: new Date().toISOString()
    });
  }

  next();
};

/**
 * Async request validation wrapper
 * @param {Array} validations - Array of validation rules
 * @returns {Function} - Express middleware function
 */
const asyncValidateRequest = (validations) => {
  return async (req, res, next) => {
    try {
      // Run all validations
      await Promise.all(validations.map(validation => validation.run(req)));

      // Check for validation errors
      validateRequest(req, res, next);
    } catch (error) {
      logger.error('Validation error:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Validation error occurred',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  };
};

module.exports = { validateRequest, asyncValidateRequest };
