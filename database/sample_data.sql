-- Sample Data for Appointment Booking Chatbot Database
-- This file contains sample data for testing and demonstration purposes

-- Insert sample appointment types
INSERT INTO appointment_types (name, description, default_duration_minutes) VALUES
('consultation', 'Initial consultation and examination', 60),
('cleaning', 'Regular dental cleaning and checkup', 45),
('treatment', 'Specific dental treatment or procedure', 90),
('follow_up', 'Follow-up appointment after treatment', 30),
('emergency', 'Emergency dental care', 60),
('orthodontic', 'Orthodontic consultation or adjustment', 45),
('cosmetic', 'Cosmetic dental procedures', 120);

-- Insert sample providers
INSERT INTO providers (name, email, phone, specialization) VALUES
('Dr. Sarah Johnson', 'sarah.johnson@dentalclinic.com', '+1-555-0101', 'General Dentistry'),
('Dr. Michael Chen', 'michael.chen@dentalclinic.com', '+1-555-0102', 'Orthodontics'),
('Dr. Emily Rodriguez', 'emily.rodriguez@dentalclinic.com', '+1-555-0103', 'Periodontics'),
('Dr. James Wilson', 'james.wilson@dentalclinic.com', '+1-555-0104', 'Oral Surgery'),
('Dr. Lisa Thompson', 'lisa.thompson@dentalclinic.com', '+1-555-0105', 'Pediatric Dentistry');

-- Insert sample users (password hash is for 'password123' - for demo purposes only)
INSERT INTO users (email, password_hash, first_name, last_name, phone, date_of_birth, emergency_contact_name, emergency_contact_phone, insurance_provider, insurance_number, preferred_language, timezone, is_verified) VALUES
('john.doe@email.com', '$2b$10$rQZ8K9vQZ8K9vQZ8K9vQZ8O', 'John', 'Doe', '+1-555-1001', '1985-03-15', 'Jane Doe', '+1-555-1002', 'BlueCross BlueShield', 'BC123456789', 'en', 'America/New_York', true),
('jane.smith@email.com', '$2b$10$rQZ8K9vQZ8K9vQZ8K9vQZ8O', 'Jane', 'Smith', '+1-555-1003', '1990-07-22', 'Bob Smith', '+1-555-1004', 'Aetna', 'AE987654321', 'en', 'America/Los_Angeles', true),
('mike.johnson@email.com', '$2b$10$rQZ8K9vQZ8K9vQZ8K9vQZ8O', 'Mike', 'Johnson', '+1-555-1005', '1978-11-08', 'Sarah Johnson', '+1-555-1006', 'Cigna', 'CI456789123', 'en', 'America/Chicago', true),
('sarah.wilson@email.com', '$2b$10$rQZ8K9vQZ8K9vQZ8K9vQZ8O', 'Sarah', 'Wilson', '+1-555-1007', '1992-05-30', 'Tom Wilson', '+1-555-1008', 'UnitedHealth', 'UH789123456', 'en', 'America/Denver', true),
('david.brown@email.com', '$2b$10$rQZ8K9vQZ8K9vQZ8K9vQZ8O', 'David', 'Brown', '+1-555-1009', '1988-12-12', 'Lisa Brown', '+1-555-1010', 'Kaiser Permanente', 'KP321654987', 'en', 'America/Phoenix', false);

-- Insert sample appointments
INSERT INTO appointments (user_id, appointment_type, appointment_date, appointment_time, duration_minutes, status, provider_name, provider_email, location, notes, special_requirements) VALUES
((SELECT id FROM users WHERE email = 'john.doe@email.com'), 'consultation', '2024-01-15', '09:00:00', 60, 'confirmed', 'Dr. Sarah Johnson', 'sarah.johnson@dentalclinic.com', 'Main Office - Room 101', 'First-time patient consultation', 'Wheelchair accessible'),
((SELECT id FROM users WHERE email = 'jane.smith@email.com'), 'cleaning', '2024-01-16', '14:30:00', 45, 'scheduled', 'Dr. Sarah Johnson', 'sarah.johnson@dentalclinic.com', 'Main Office - Room 102', 'Regular cleaning appointment', NULL),
((SELECT id FROM users WHERE email = 'mike.johnson@email.com'), 'treatment', '2024-01-17', '10:15:00', 90, 'confirmed', 'Dr. Emily Rodriguez', 'emily.rodriguez@dentalclinic.com', 'Main Office - Room 103', 'Root canal treatment', 'Nitrous oxide requested'),
((SELECT id FROM users WHERE email = 'sarah.wilson@email.com'), 'orthodontic', '2024-01-18', '15:45:00', 45, 'scheduled', 'Dr. Michael Chen', 'michael.chen@dentalclinic.com', 'Orthodontic Suite - Room 201', 'Braces adjustment', NULL),
((SELECT id FROM users WHERE email = 'david.brown@email.com'), 'follow_up', '2024-01-19', '11:30:00', 30, 'scheduled', 'Dr. James Wilson', 'james.wilson@dentalclinic.com', 'Main Office - Room 104', 'Post-surgery follow-up', NULL);

-- Insert sample chat sessions
INSERT INTO chat_sessions (user_id, session_token, status, intent, language, ip_address, started_at) VALUES
((SELECT id FROM users WHERE email = 'john.doe@email.com'), 'sess_abc123def456', 'completed', 'book_appointment', 'en', '192.168.1.100', '2024-01-10 10:30:00+00'),
((SELECT id FROM users WHERE email = 'jane.smith@email.com'), 'sess_xyz789uvw012', 'active', 'reschedule', 'en', '192.168.1.101', '2024-01-11 14:20:00+00'),
((SELECT id FROM users WHERE email = 'mike.johnson@email.com'), 'sess_mno345pqr678', 'completed', 'general_inquiry', 'en', '192.168.1.102', '2024-01-12 09:15:00+00'),
(NULL, 'sess_guest_123456', 'completed', 'book_appointment', 'en', '192.168.1.103', '2024-01-13 16:45:00+00'),
((SELECT id FROM users WHERE email = 'sarah.wilson@email.com'), 'sess_stu901vwx234', 'active', 'cancel', 'en', '192.168.1.104', '2024-01-14 11:10:00+00');

-- Insert sample chat messages
INSERT INTO chat_messages (session_id, message_type, content, intent, entities, confidence_score, processing_time_ms) VALUES
-- Session 1: John Doe booking appointment
((SELECT id FROM chat_sessions WHERE session_token = 'sess_abc123def456'), 'user', 'Hi, I need to book a dental appointment', 'book_appointment', '{"service": "dental appointment"}', 0.95, 120),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_abc123def456'), 'assistant', 'Hello! I''d be happy to help you book a dental appointment. What type of appointment are you looking for?', NULL, NULL, NULL, 150),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_abc123def456'), 'user', 'I need a consultation with a dentist', 'book_appointment', '{"appointment_type": "consultation"}', 0.92, 110),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_abc123def456'), 'assistant', 'Great! I can help you schedule a consultation. What date works best for you?', NULL, NULL, NULL, 140),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_abc123def456'), 'user', 'How about January 15th at 9 AM?', 'book_appointment', '{"date": "2024-01-15", "time": "09:00"}', 0.88, 130),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_abc123def456'), 'assistant', 'Perfect! I have January 15th at 9:00 AM available. I''ll book that consultation for you with Dr. Sarah Johnson. Is there anything else I can help you with?', NULL, NULL, NULL, 160),

-- Session 2: Jane Smith rescheduling
((SELECT id FROM chat_sessions WHERE session_token = 'sess_xyz789uvw012'), 'user', 'I need to reschedule my appointment', 'reschedule', '{"action": "reschedule"}', 0.94, 125),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_xyz789uvw012'), 'assistant', 'I can help you reschedule your appointment. What is your current appointment date and what new date would you prefer?', NULL, NULL, NULL, 145),

-- Session 3: Mike Johnson general inquiry
((SELECT id FROM chat_sessions WHERE session_token = 'sess_mno345pqr678'), 'user', 'What are your office hours?', 'general_inquiry', '{"question_type": "hours"}', 0.90, 100),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_mno345pqr678'), 'assistant', 'Our office hours are Monday through Friday, 8:00 AM to 6:00 PM, and Saturday 9:00 AM to 2:00 PM. We are closed on Sundays.', NULL, NULL, NULL, 180),

-- Session 4: Guest user booking
((SELECT id FROM chat_sessions WHERE session_token = 'sess_guest_123456'), 'user', 'I want to book a cleaning appointment', 'book_appointment', '{"appointment_type": "cleaning"}', 0.93, 115),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_guest_123456'), 'assistant', 'I''d be happy to help you book a cleaning appointment. Since you''re not logged in, I''ll need some basic information first. What''s your name and contact information?', NULL, NULL, NULL, 155),

-- Session 5: Sarah Wilson cancelling
((SELECT id FROM chat_sessions WHERE session_token = 'sess_stu901vwx234'), 'user', 'I need to cancel my appointment', 'cancel', '{"action": "cancel"}', 0.96, 105),
((SELECT id FROM chat_sessions WHERE session_token = 'sess_stu901vwx234'), 'assistant', 'I can help you cancel your appointment. Which appointment would you like to cancel?', NULL, NULL, NULL, 135);

-- Insert sample user preferences
INSERT INTO user_preferences (user_id, notification_preferences, appointment_reminders, preferred_communication, timezone) VALUES
((SELECT id FROM users WHERE email = 'john.doe@email.com'), '{"email": true, "sms": true, "push": true}', '{"email_24h": true, "sms_2h": true, "email_1h": false}', 'email', 'America/New_York'),
((SELECT id FROM users WHERE email = 'jane.smith@email.com'), '{"email": true, "sms": false, "push": true}', '{"email_24h": true, "sms_2h": false, "email_1h": true}', 'email', 'America/Los_Angeles'),
((SELECT id FROM users WHERE email = 'mike.johnson@email.com'), '{"email": false, "sms": true, "push": false}', '{"email_24h": false, "sms_2h": true, "email_1h": false}', 'sms', 'America/Chicago'),
((SELECT id FROM users WHERE email = 'sarah.wilson@email.com'), '{"email": true, "sms": true, "push": true}', '{"email_24h": true, "sms_2h": true, "email_1h": true}', 'email', 'America/Denver'),
((SELECT id FROM users WHERE email = 'david.brown@email.com'), '{"email": true, "sms": true, "push": false}', '{"email_24h": true, "sms_2h": true, "email_1h": false}', 'email', 'America/Phoenix');

-- Insert sample audit logs
INSERT INTO audit_logs (user_id, action, resource_type, resource_id, old_values, new_values, ip_address, user_agent) VALUES
((SELECT id FROM users WHERE email = 'john.doe@email.com'), 'appointment_created', 'appointment', (SELECT id FROM appointments WHERE user_id = (SELECT id FROM users WHERE email = 'john.doe@email.com') LIMIT 1), NULL, '{"appointment_type": "consultation", "date": "2024-01-15", "time": "09:00:00"}', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
((SELECT id FROM users WHERE email = 'jane.smith@email.com'), 'appointment_updated', 'appointment', (SELECT id FROM appointments WHERE user_id = (SELECT id FROM users WHERE email = 'jane.smith@email.com') LIMIT 1), '{"status": "scheduled"}', '{"status": "confirmed"}', '192.168.1.101', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'),
((SELECT id FROM users WHERE email = 'mike.johnson@email.com'), 'user_login', 'user', (SELECT id FROM users WHERE email = 'mike.johnson@email.com'), NULL, '{"last_login": "2024-01-12T09:15:00Z"}', '192.168.1.102', 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15');

-- Update some chat sessions to have ended_at timestamps
UPDATE chat_sessions
SET ended_at = started_at + INTERVAL '5 minutes'
WHERE session_token IN ('sess_abc123def456', 'sess_mno345pqr678', 'sess_guest_123456');

-- Update some appointments to have different statuses
UPDATE appointments
SET status = 'completed', updated_at = CURRENT_TIMESTAMP
WHERE appointment_date < CURRENT_DATE - INTERVAL '1 day';

-- Create some additional sample data for testing
INSERT INTO appointments (user_id, appointment_type, appointment_date, appointment_time, duration_minutes, status, provider_name, provider_email, location, notes) VALUES
((SELECT id FROM users WHERE email = 'john.doe@email.com'), 'cleaning', '2024-02-01', '10:00:00', 45, 'scheduled', 'Dr. Sarah Johnson', 'sarah.johnson@dentalclinic.com', 'Main Office - Room 101', 'Follow-up cleaning'),
((SELECT id FROM users WHERE email = 'jane.smith@email.com'), 'treatment', '2024-02-05', '14:00:00', 120, 'scheduled', 'Dr. Emily Rodriguez', 'emily.rodriguez@dentalclinic.com', 'Main Office - Room 103', 'Crown placement'),
((SELECT id FROM users WHERE email = 'mike.johnson@email.com'), 'follow_up', '2024-02-10', '11:00:00', 30, 'scheduled', 'Dr. James Wilson', 'james.wilson@dentalclinic.com', 'Main Office - Room 104', 'Post-treatment checkup');

-- Insert additional chat sessions for testing
INSERT INTO chat_sessions (user_id, session_token, status, intent, language, ip_address, started_at, ended_at) VALUES
((SELECT id FROM users WHERE email = 'john.doe@email.com'), 'sess_test_001', 'completed', 'book_appointment', 'en', '192.168.1.105', '2024-01-08 13:30:00+00', '2024-01-08 13:45:00+00'),
((SELECT id FROM users WHERE email = 'jane.smith@email.com'), 'sess_test_002', 'completed', 'general_inquiry', 'en', '192.168.1.106', '2024-01-09 16:20:00+00', '2024-01-09 16:35:00+00'),
(NULL, 'sess_guest_002', 'completed', 'book_appointment', 'en', '192.168.1.107', '2024-01-07 09:45:00+00', '2024-01-07 10:00:00+00');
