const { query } = require('../utils/database');
const bcrypt = require('bcryptjs');
const logger = require('../utils/logger');

const createUser = async (userData) => {
  try {
    const { email, password, firstName, lastName, phone, dateOfBirth } = userData;

    // Hash password
    const saltRounds = parseInt(process.env.BCRYPT_ROUNDS) || 12;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    const result = await query(
      `INSERT INTO users (email, password_hash, first_name, last_name, phone, date_of_birth, is_verified)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id, email, first_name, last_name, phone, date_of_birth, is_verified, created_at`,
      [email, passwordHash, firstName, lastName, phone, dateOfBirth, false]
    );

    logger.info('User created successfully', { userId: result.rows[0].id, email });
    return result.rows[0];
  } catch (error) {
    logger.error('Error creating user:', error);
    throw error;
  }
};

const getUserByEmail = async (email) => {
  try {
    const result = await query(
      'SELECT * FROM users WHERE email = $1',
      [email]
    );

    return result.rows[0] || null;
  } catch (error) {
    logger.error('Error getting user by email:', error);
    throw error;
  }
};

const getUserById = async (id) => {
  try {
    const result = await query(
      'SELECT * FROM users WHERE id = $1',
      [id]
    );

    return result.rows[0] || null;
  } catch (error) {
    logger.error('Error getting user by ID:', error);
    throw error;
  }
};

const updateUser = async (id, updateData) => {
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

    values.push(id);
    const result = await query(
      `UPDATE users SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP
       WHERE id = $${paramCount}
       RETURNING *`,
      values
    );

    logger.info('User updated successfully', { userId: id });
    return result.rows[0];
  } catch (error) {
    logger.error('Error updating user:', error);
    throw error;
  }
};

const verifyPassword = async (password, hashedPassword) => {
  try {
    return await bcrypt.compare(password, hashedPassword);
  } catch (error) {
    logger.error('Error verifying password:', error);
    throw error;
  }
};

module.exports = {
  createUser,
  getUserByEmail,
  getUserById,
  updateUser,
  verifyPassword
};
