const express = require('express');
const jwt = require('jsonwebtoken');
const { body } = require('express-validator');
const { validateRequest } = require('../middleware/validateRequest');
const { createUser, getUserByEmail, verifyPassword } = require('../models/User');
const logger = require('../utils/logger');

const router = express.Router();

// Generate JWT token
const generateToken = (userId) => {
  return jwt.sign(
    { userId },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRES_IN || '24h' }
  );
};

// Generate refresh token
const generateRefreshToken = (userId) => {
  return jwt.sign(
    { userId, type: 'refresh' },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d' }
  );
};

/**
 * @route   POST /api/auth/register
 * @desc    Register a new user
 * @access  Public
 */
router.post('/register',
  [
    body('email').isEmail().normalizeEmail().withMessage('Valid email is required'),
    body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters'),
    body('firstName').notEmpty().trim().withMessage('First name is required'),
    body('lastName').notEmpty().trim().withMessage('Last name is required'),
    body('phone').optional().isMobilePhone().withMessage('Valid phone number is required'),
    body('dateOfBirth').optional().isISO8601().withMessage('Valid date of birth is required')
  ],
  validateRequest,
  async (req, res) => {
    try {
      const { email, password, firstName, lastName, phone, dateOfBirth } = req.body;

      // Check if user already exists
      const existingUser = await getUserByEmail(email);
      if (existingUser) {
        return res.status(409).json({
          success: false,
          error: {
            message: 'User with this email already exists'
          },
          timestamp: new Date().toISOString()
        });
      }

      // Create new user
      const user = await createUser({
        email,
        password,
        firstName,
        lastName,
        phone,
        dateOfBirth
      });

      // Generate tokens
      const token = generateToken(user.id);
      const refreshToken = generateRefreshToken(user.id);

      logger.info('User registered successfully', { userId: user.id, email });

      res.status(201).json({
        success: true,
        data: {
          user: {
            id: user.id,
            email: user.email,
            firstName: user.first_name,
            lastName: user.last_name,
            phone: user.phone,
            isVerified: user.is_verified
          },
          token,
          refreshToken
        },
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Registration error:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Registration failed',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   POST /api/auth/login
 * @desc    Login user
 * @access  Public
 */
router.post('/login',
  [
    body('email').isEmail().normalizeEmail().withMessage('Valid email is required'),
    body('password').notEmpty().withMessage('Password is required')
  ],
  validateRequest,
  async (req, res) => {
    try {
      const { email, password } = req.body;

      // Get user by email
      const user = await getUserByEmail(email);
      if (!user) {
        return res.status(401).json({
          success: false,
          error: {
            message: 'Invalid email or password'
          },
          timestamp: new Date().toISOString()
        });
      }

      // Verify password
      const isPasswordValid = await verifyPassword(password, user.password_hash);
      if (!isPasswordValid) {
        return res.status(401).json({
          success: false,
          error: {
            message: 'Invalid email or password'
          },
          timestamp: new Date().toISOString()
        });
      }

      // Check if user is active
      if (!user.is_active) {
        return res.status(401).json({
          success: false,
          error: {
            message: 'Account is deactivated'
          },
          timestamp: new Date().toISOString()
        });
      }

      // Generate tokens
      const token = generateToken(user.id);
      const refreshToken = generateRefreshToken(user.id);

      logger.info('User logged in successfully', { userId: user.id, email });

      res.status(200).json({
        success: true,
        data: {
          user: {
            id: user.id,
            email: user.email,
            firstName: user.first_name,
            lastName: user.last_name,
            phone: user.phone,
            isVerified: user.is_verified
          },
          token,
          refreshToken
        },
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Login error:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Login failed',
          details: error.message
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   POST /api/auth/refresh
 * @desc    Refresh access token
 * @access  Public
 */
router.post('/refresh',
  [
    body('token').notEmpty().withMessage('Refresh token is required')
  ],
  validateRequest,
  async (req, res) => {
    try {
      const { token } = req.body;

      // Verify refresh token
      const decoded = jwt.verify(token, process.env.JWT_SECRET);

      if (decoded.type !== 'refresh') {
        return res.status(401).json({
          success: false,
          error: {
            message: 'Invalid token type'
          },
          timestamp: new Date().toISOString()
        });
      }

      // Generate new access token
      const newToken = generateToken(decoded.userId);

      res.status(200).json({
        success: true,
        data: {
          token: newToken
        },
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Token refresh error:', error);
      res.status(401).json({
        success: false,
        error: {
          message: 'Invalid or expired refresh token'
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

/**
 * @route   GET /api/auth/me
 * @desc    Get current user
 * @access  Private
 */
router.get('/me', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        error: {
          message: 'Access denied. No token provided.'
        },
        timestamp: new Date().toISOString()
      });
    }

    const token = authHeader.substring(7);
    const decoded = jwt.verify(token, process.env.JWT_SECRET);

    // Get user from database
    const { getUserById } = require('../models/User');
    const user = await getUserById(decoded.userId);

    if (!user) {
      return res.status(401).json({
        success: false,
        error: {
          message: 'User not found'
        },
        timestamp: new Date().toISOString()
      });
    }

    res.status(200).json({
      success: true,
      data: {
        user: {
          id: user.id,
          email: user.email,
          firstName: user.first_name,
          lastName: user.last_name,
          phone: user.phone,
          isVerified: user.is_verified
        }
      },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Get user error:', error);
    res.status(401).json({
      success: false,
      error: {
        message: 'Invalid token'
      },
      timestamp: new Date().toISOString()
    });
  }
});

module.exports = router;
