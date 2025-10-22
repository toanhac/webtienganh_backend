from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import secrets
import os

app = Flask(__name__)
CORS(app)

# PostgreSQL Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 
    'postgresql://webtienganh_db_user:yRS7EbwmXeLDDNxTvbGZgMOo0gU2BLqc@dpg-d3s1if9r0fns73e5oui0-a.singapore-postgres.render.com/webtienganh_db')

def get_db_connection():
    """Create a PostgreSQL database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create flashcards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            unit INTEGER NOT NULL,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default_flashcards table (templates for new users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS default_flashcards (
            id SERIAL PRIMARY KEY,
            unit INTEGER NOT NULL,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create exercises table (same for all users, managed by admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id SERIAL PRIMARY KEY,
            unit INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer VARCHAR(1) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create exercise_results table (track user performance)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_results (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            exercise_id INTEGER NOT NULL,
            user_answer VARCHAR(1) NOT NULL,
            is_correct INTEGER NOT NULL,
            session_id VARCHAR(255),
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exercise_id) REFERENCES exercises (id)
        )
    ''')
    
    # Create exercise_sessions table (track complete exercise attempts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            unit INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create admin user if not exists
    admin_email = 'admin@quizzmate.com'
    admin_password = hashlib.sha256('admin123'.encode()).hexdigest()  # Default admin password
    cursor.execute('SELECT * FROM users WHERE email = %s', (admin_email,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)',
            ('Admin', admin_email, admin_password, 1)
        )
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token():
    """Generate a random session token"""
    return secrets.token_hex(32)

# User Management
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user already exists
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        conn.close()
        return jsonify({"success": False, "message": "Email already registered"}), 400
    
    # Create new user
    hashed_password = hash_password(password)
    cursor.execute(
        'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
        (username, email, hashed_password)
    )
    
    # Copy default flashcards to new user
    cursor.execute('SELECT unit, front, back FROM default_flashcards')
    default_cards = cursor.fetchall()
    
    for card in default_cards:
        cursor.execute(
            'INSERT INTO flashcards (email, unit, front, back) VALUES (%s, %s, %s, %s)',
            (email, card['unit'], card['front'], card['back'])
        )
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "User registered successfully"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    hashed_password = hash_password(password)
    
    # Find user
    cursor.execute(
        'SELECT username, email, is_admin FROM users WHERE email = %s AND password = %s',
        (email, hashed_password)
    )
    user = cursor.fetchone()
    
    if user:
        # Generate session token
        token = generate_session_token()
        cursor.execute(
            'INSERT INTO sessions (email, token) VALUES (%s, %s)',
            (email, token)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "username": user['username'],
            "email": user['email'],
            "token": token,
            "is_admin": bool(user['is_admin'])
        })
    
    conn.close()
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    email = data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Remove session
    cursor.execute('DELETE FROM sessions WHERE email = %s', (email,))
    rows_affected = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    if rows_affected > 0:
        return jsonify({"success": True, "message": "Logged out successfully"})
    
    return jsonify({"success": False, "message": "User not logged in"}), 400

def get_user_from_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Find session by token
    cursor.execute('SELECT email FROM sessions WHERE token = %s', (token,))
    session = cursor.fetchone()
    
    if session:
        # Find user by email
        cursor.execute(
            'SELECT username, email FROM users WHERE email = %s',
            (session['email'],)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
    
    conn.close()
    return None

# Admin Management
@app.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) as total_users FROM users WHERE is_admin = 0')
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as total_flashcards FROM flashcards')
    total_flashcards = cursor.fetchone()['total_flashcards']
    
    cursor.execute('SELECT COUNT(*) as total_default_cards FROM default_flashcards')
    total_default_cards = cursor.fetchone()['total_default_cards']
    
    cursor.execute('SELECT COUNT(DISTINCT unit) as total_units FROM default_flashcards')
    total_units = cursor.fetchone()['total_units']
    
    conn.close()
    
    return jsonify({
        "success": True,
        "stats": {
            "total_users": total_users,
            "total_flashcards": total_flashcards,
            "total_default_cards": total_default_cards,
            "total_units": total_units
        }
    })

@app.route('/admin/default-flashcards', methods=['GET'])
def get_default_flashcards():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    unit = request.args.get('unit', type=int)
    
    if unit:
        cursor.execute(
            'SELECT id, unit, front, back FROM default_flashcards WHERE unit = %s',
            (unit,)
        )
    else:
        cursor.execute('SELECT id, unit, front, back FROM default_flashcards')
    
    flashcards = cursor.fetchall()
    conn.close()
    
    default_cards = [dict(card) for card in flashcards]
    
    return jsonify({"success": True, "cards": default_cards})

@app.route('/admin/default-flashcards', methods=['POST'])
def add_default_flashcard():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    data = request.json
    front = data.get('front')
    back = data.get('back')
    unit = data.get('unit')

    if not front or not back or not unit:
        conn.close()
        return jsonify({"success": False, "message": "Front, back, and unit are required"}), 400
    
    # Insert new default flashcard
    cursor.execute(
        'INSERT INTO default_flashcards (unit, front, back) VALUES (%s, %s, %s) RETURNING id',
        (unit, front, back)
    )
    
    result = cursor.fetchone()
    card_id = result['id']
    conn.commit()
    conn.close()
    
    new_card = {
        "id": card_id,
        "unit": unit,
        "front": front,
        "back": back
    }
    
    return jsonify({"success": True, "message": "Default flashcard added", "card": new_card}), 201

@app.route('/admin/default-flashcards/<int:card_id>', methods=['PUT'])
def update_default_flashcard(card_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    data = request.json
    front = data.get('front')
    back = data.get('back')

    if not front or not back:
        conn.close()
        return jsonify({"success": False, "message": "Front and back are required"}), 400
    
    # Update default flashcard
    cursor.execute(
        'UPDATE default_flashcards SET front = %s, back = %s WHERE id = %s',
        (front, back, card_id)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Card not found"}), 404
    
    return jsonify({"success": True, "message": "Default flashcard updated"})

@app.route('/admin/default-flashcards/<int:card_id>', methods=['DELETE'])
def delete_default_flashcard(card_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    # Delete default flashcard
    cursor.execute('DELETE FROM default_flashcards WHERE id = %s', (card_id,))
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Card not found"}), 404
    
    return jsonify({"success": True, "message": "Default flashcard deleted"})

# Flashcard Management
@app.route('/flashcards', methods=['GET'])
def get_flashcards():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    unit = request.args.get('unit', type=int)
    if not unit:
        return jsonify({"success": False, "message": "Unit parameter is required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Filter flashcards for the current user and unit
    cursor.execute(
        'SELECT id, email, unit, front, back FROM flashcards WHERE email = %s AND unit = ?',
        (user['email'], unit)
    )
    flashcards = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    user_flashcards = [dict(card) for card in flashcards]
    
    return jsonify(user_flashcards)

@app.route('/flashcards', methods=['POST'])
def add_flashcard():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.json
    front = data.get('front')
    back = data.get('back')
    unit = data.get('unit')

    if not front or not back or not unit:
        return jsonify({"success": False, "message": "Front, back, and unit are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Insert new flashcard
    cursor.execute(
        'INSERT INTO flashcards (email, unit, front, back) VALUES (%s, %s, %s, %s) RETURNING id',
        (user['email'], unit, front, back)
    )
    
    result = cursor.fetchone()
    card_id = result['id']
    conn.commit()
    conn.close()
    
    new_card = {
        "id": card_id,
        "email": user['email'],
        "unit": unit,
        "front": front,
        "back": back
    }
    
    return jsonify({"success": True, "message": "Flashcard added", "card": new_card}), 201

@app.route('/flashcards/<int:card_id>', methods=['PUT'])
def update_flashcard(card_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.json
    front = data.get('front')
    back = data.get('back')

    if not front or not back:
        return jsonify({"success": False, "message": "Front and back are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Update flashcard if it belongs to the user
    cursor.execute(
        'UPDATE flashcards SET front = %s, back = %s WHERE id = %s AND email = %s',
        (front, back, card_id, user['email'])
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Card not found or not owned by user"}), 404
    
    return jsonify({"success": True, "message": "Flashcard updated"})

@app.route('/flashcards/<int:card_id>', methods=['DELETE'])
def delete_flashcard(card_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Delete flashcard if it belongs to the user
    cursor.execute(
        'DELETE FROM flashcards WHERE id = %s AND email = %s',
        (card_id, user['email'])
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Card not found or not owned by user"}), 404
    
    return jsonify({"success": True, "message": "Flashcard deleted"})

# Exercise Management
@app.route('/exercises', methods=['GET'])
def get_exercises():
    """Get exercises for a specific unit"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    unit = request.args.get('unit', type=int)
    if not unit:
        return jsonify({"success": False, "message": "Unit parameter is required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        'SELECT id, unit, question, option_a, option_b, option_c, option_d, correct_answer FROM exercises WHERE unit = %s',
        (unit,)
    )
    exercises = cursor.fetchall()
    conn.close()
    
    exercise_list = [dict(ex) for ex in exercises]
    
    return jsonify({"success": True, "exercises": exercise_list})

@app.route('/exercises/submit', methods=['POST'])
def submit_exercise_answer():
    """Record exercise answer result (answer is checked on frontend)"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    exercise_id = data.get('exercise_id')
    user_answer = data.get('user_answer')
    is_correct = data.get('is_correct', False)  # Frontend sends this
    session_id = data.get('session_id')  # Optional session ID
    
    if not exercise_id or not user_answer:
        return jsonify({"success": False, "message": "Exercise ID and answer are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Just record the result (trust the frontend since answers are already sent there)
    cursor.execute(
        'INSERT INTO exercise_results (email, exercise_id, user_answer, is_correct, session_id) VALUES (%s, %s, %s, %s, %s)',
        (user['email'], exercise_id, user_answer, 1 if is_correct else 0, session_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/exercises/submit-session', methods=['POST'])
def submit_exercise_session():
    """Submit a complete exercise session (counts as 1 attempt)"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    results = data.get('results', [])  # Array of {exercise_id, user_answer, is_correct}
    unit = data.get('unit')
    
    if not results or not unit:
        return jsonify({"success": False, "message": "Results and unit are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Generate unique session ID
    session_id = secrets.token_hex(16)
    
    # Calculate session statistics
    total_questions = len(results)
    correct_answers = sum(1 for r in results if r.get('is_correct'))
    
    try:
        # Insert session record
        cursor.execute(
            'INSERT INTO exercise_sessions (session_id, email, unit, total_questions, correct_answers) VALUES (%s, %s, %s, %s, %s)',
            (session_id, user['email'], unit, total_questions, correct_answers)
        )
        
        # Insert individual results with session_id
        for result in results:
            cursor.execute(
                'INSERT INTO exercise_results (email, exercise_id, user_answer, is_correct, session_id) VALUES (%s, %s, %s, %s, %s)',
                (user['email'], result['exercise_id'], result['user_answer'], 1 if result['is_correct'] else 0, session_id)
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/exercises/statistics', methods=['GET'])
def get_exercise_statistics():
    """Get exercise statistics for the current user (based on sessions, not individual questions)"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get overall statistics from sessions
    cursor.execute(
        'SELECT COUNT(*) as total, SUM(total_questions) as total_questions, SUM(correct_answers) as correct FROM exercise_sessions WHERE email = %s',
        (user['email'],)
    )
    overall = cursor.fetchone()
    
    # Get statistics by unit from sessions
    cursor.execute('''
        SELECT unit, COUNT(*) as attempts, SUM(total_questions) as total, SUM(correct_answers) as correct
        FROM exercise_sessions
        WHERE email = %s
        GROUP BY unit
        ORDER BY unit
    ''', (user['email'],))
    
    by_unit = cursor.fetchall()
    conn.close()
    
    unit_stats = [dict(row) for row in by_unit]
    
    # Total attempts = number of sessions completed
    total_attempts = overall['total'] or 0
    total_questions_answered = overall['total_questions'] or 0
    total_correct = overall['correct'] or 0
    
    return jsonify({
        "success": True,
        "overall": {
            "total": total_attempts,  # Number of complete sessions
            "total_questions": total_questions_answered,  # Total questions across all sessions
            "correct": total_correct,
            "accuracy": round((total_correct) / (total_questions_answered or 1) * 100, 2) if total_questions_answered else 0
        },
        "by_unit": unit_stats
    })

# Admin Exercise Management
@app.route('/admin/exercises', methods=['GET'])
def get_admin_exercises():
    """Admin: Get all exercises or exercises for a specific unit"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    unit = request.args.get('unit', type=int)
    
    if unit:
        cursor.execute(
            'SELECT id, unit, question, option_a, option_b, option_c, option_d, correct_answer FROM exercises WHERE unit = %s',
            (unit,)
        )
    else:
        cursor.execute('SELECT id, unit, question, option_a, option_b, option_c, option_d, correct_answer FROM exercises')
    
    exercises = cursor.fetchall()
    conn.close()
    
    exercise_list = [dict(ex) for ex in exercises]
    
    return jsonify({"success": True, "exercises": exercise_list})

@app.route('/admin/exercises', methods=['POST'])
def add_admin_exercise():
    """Admin: Add a new exercise"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    data = request.json
    unit = data.get('unit')
    question = data.get('question')
    option_a = data.get('option_a')
    option_b = data.get('option_b')
    option_c = data.get('option_c')
    option_d = data.get('option_d')
    correct_answer = data.get('correct_answer')
    
    if not all([unit, question, option_a, option_b, option_c, option_d, correct_answer]):
        conn.close()
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    if correct_answer not in ['A', 'B', 'C', 'D']:
        conn.close()
        return jsonify({"success": False, "message": "Correct answer must be A, B, C, or D"}), 400
    
    # Insert new exercise
    cursor.execute(
        'INSERT INTO exercises (unit, question, option_a, option_b, option_c, option_d, correct_answer) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id',
        (unit, question, option_a, option_b, option_c, option_d, correct_answer)
    )
    
    result = cursor.fetchone()
    exercise_id = result['id']
    conn.commit()
    conn.close()
    
    new_exercise = {
        "id": exercise_id,
        "unit": unit,
        "question": question,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_d": option_d,
        "correct_answer": correct_answer
    }
    
    return jsonify({"success": True, "message": "Exercise added", "exercise": new_exercise}), 201

@app.route('/admin/exercises/<int:exercise_id>', methods=['PUT'])
def update_admin_exercise(exercise_id):
    """Admin: Update an existing exercise"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    data = request.json
    question = data.get('question')
    option_a = data.get('option_a')
    option_b = data.get('option_b')
    option_c = data.get('option_c')
    option_d = data.get('option_d')
    correct_answer = data.get('correct_answer')
    
    if not all([question, option_a, option_b, option_c, option_d, correct_answer]):
        conn.close()
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    if correct_answer not in ['A', 'B', 'C', 'D']:
        conn.close()
        return jsonify({"success": False, "message": "Correct answer must be A, B, C, or D"}), 400
    
    # Update exercise
    cursor.execute(
        'UPDATE exercises SET question = %s, option_a = %s, option_b = %s, option_c = %s, option_d = %s, correct_answer = %s WHERE id = %s',
        (question, option_a, option_b, option_c, option_d, correct_answer, exercise_id)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Exercise not found"}), 404
    
    return jsonify({"success": True, "message": "Exercise updated"})

@app.route('/admin/exercises/<int:exercise_id>', methods=['DELETE'])
def delete_admin_exercise(exercise_id):
    """Admin: Delete an exercise"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    # Delete exercise
    cursor.execute('DELETE FROM exercises WHERE id = %s', (exercise_id,))
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Exercise not found"}), 404
    
    return jsonify({"success": True, "message": "Exercise deleted"})

@app.route('/admin/exercises/statistics', methods=['GET'])
def get_admin_exercise_statistics():
    """Admin: Get exercise statistics for all users"""
    user = get_user_from_token(request)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user is admin
    cursor.execute('SELECT is_admin FROM users WHERE email = %s', (user['email'],))
    user_data = cursor.fetchone()
    
    if not user_data or not user_data['is_admin']:
        conn.close()
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    # Get total exercises count
    cursor.execute('SELECT COUNT(*) as total_exercises FROM exercises')
    total_exercises = cursor.fetchone()['total_exercises']
    
    # Get total attempts
    cursor.execute('SELECT COUNT(*) as total_attempts FROM exercise_results')
    total_attempts = cursor.fetchone()['total_attempts']
    
    # Get correct attempts
    cursor.execute('SELECT COUNT(*) as correct_attempts FROM exercise_results WHERE is_correct = 1')
    correct_attempts = cursor.fetchone()['correct_attempts']
    
    # Get statistics per user
    cursor.execute('''
        SELECT u.email, u.username, 
               COUNT(er.id) as total_attempts,
               SUM(er.is_correct) as correct_attempts
        FROM users u
        LEFT JOIN exercise_results er ON u.email = er.email
        WHERE u.is_admin = 0
        GROUP BY u.email, u.username
        ORDER BY total_attempts DESC
    ''')
    
    user_stats = cursor.fetchall()
    conn.close()
    
    user_statistics = [dict(row) for row in user_stats]
    
    return jsonify({
        "success": True,
        "stats": {
            "total_exercises": total_exercises,
            "total_attempts": total_attempts,
            "correct_attempts": correct_attempts or 0,
            "accuracy": round((correct_attempts or 0) / (total_attempts or 1) * 100, 2) if total_attempts else 0
        },
        "user_stats": user_statistics
    })

if __name__ == '__main__':
    app.run(debug=True, port=8000)
