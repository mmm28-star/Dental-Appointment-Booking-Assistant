const express = require('express');
const { body, param } = require('express-validator');
const { authenticate } = require('../middleware/auth');
const { validateRequest } = require('../middleware/validateRequest');
const logger = require('../utils/logger');

const router = express.Router();

/**
 * @route   GET /api/appointments
 * @desc    Get user's appointments
 * @access  Private
 */
router.get('/', authenticate, async (req, res) => {
  try {
    const userId = req.user.id;

    // Mock appointments for demo
    const appointments = [
      {
        id: 'apt_123',
        type: 'cleaning',
        date: '2024-01-20',
        time: '10:00',
        provider: 'Dr. Sarah Johnson',
        status: 'confirmed'
      }
    ];

    res.status(200).json({
      success: true,
      data: appointments,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Error getting appointments:', error);
    res.status(500).json({
      success: false,
      error: {
        message: 'Failed to get appointments'
      },
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * @route   POST /api/appointments
 * @desc    Create new appointment
 * @access  Private
 */
router.post('/',
  [
    body('appointmentType').notEmpty().withMessage('Appointment type is required'),
    body('date').isISO8601().withMessage('Valid date is required'),
    body('time').matches(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/).withMessage('Valid time is required'),
    body('provider').notEmpty().withMessage('Provider is required')
  ],
  validateRequest,
  authenticate,
  async (req, res) => {
    try {
      const { appointmentType, date, time, provider, notes } = req.body;
      const userId = req.user.id;

      // Mock appointment creation
      const appointment = {
        id: `apt_${Date.now()}`,
        type: appointmentType,
        date,
        time,
        provider,
        notes,
        status: 'confirmed',
        userId
      };

      logger.info('Appointment created', { appointmentId: appointment.id, userId });

      res.status(201).json({
        success: true,
        data: appointment,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error creating appointment:', error);
      res.status(500).json({
        success: false,
        error: {
          message: 'Failed to create appointment'
        },
        timestamp: new Date().toISOString()
      });
    }
  }
);

module.exports = router;
