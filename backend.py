from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# Database configuration
DATABASE = "webtienganh.db"

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create flashcards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            unit INTEGER NOT NULL,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        conn.close()
        return jsonify({"success": False, "message": "Email already registered"}), 400
    
    # Create new user
    hashed_password = hash_password(password)
    cursor.execute(
        'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
        (username, email, hashed_password)
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
    cursor = conn.cursor()
    
    hashed_password = hash_password(password)
    
    # Find user
    cursor.execute(
        'SELECT username, email FROM users WHERE email = ? AND password = ?',
        (email, hashed_password)
    )
    user = cursor.fetchone()
    
    if user:
        # Generate session token
        token = generate_session_token()
        cursor.execute(
            'INSERT INTO sessions (email, token) VALUES (?, ?)',
            (email, token)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "username": user['username'],
            "email": user['email'],
            "token": token
        })
    
    conn.close()
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    email = data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Remove session
    cursor.execute('DELETE FROM sessions WHERE email = ?', (email,))
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
    cursor = conn.cursor()
    
    # Find session by token
    cursor.execute('SELECT email FROM sessions WHERE token = ?', (token,))
    session = cursor.fetchone()
    
    if session:
        # Find user by email
        cursor.execute(
            'SELECT username, email FROM users WHERE email = ?',
            (session['email'],)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
    
    conn.close()
    return None

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
    cursor = conn.cursor()
    
    # Filter flashcards for the current user and unit
    cursor.execute(
        'SELECT id, email, unit, front, back FROM flashcards WHERE email = ? AND unit = ?',
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
    cursor = conn.cursor()
    
    # Insert new flashcard
    cursor.execute(
        'INSERT INTO flashcards (email, unit, front, back) VALUES (?, ?, ?, ?)',
        (user['email'], unit, front, back)
    )
    
    card_id = cursor.lastrowid
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
    cursor = conn.cursor()
    
    # Update flashcard if it belongs to the user
    cursor.execute(
        'UPDATE flashcards SET front = ?, back = ? WHERE id = ? AND email = ?',
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
    cursor = conn.cursor()
    
    # Delete flashcard if it belongs to the user
    cursor.execute(
        'DELETE FROM flashcards WHERE id = ? AND email = ?',
        (card_id, user['email'])
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        return jsonify({"success": False, "message": "Card not found or not owned by user"}), 404
    
    return jsonify({"success": True, "message": "Flashcard deleted"})

if __name__ == '__main__':
    app.run(debug=True, port=8000)
