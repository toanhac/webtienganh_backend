# Web Tieng Anh - English Learning Web Application

A Flask-based web application for learning English using flashcards with user authentication and session management.

## 🚀 Features

- **User Authentication**: Register, login, and logout functionality
- **Flashcard System**: Create, read, update, and delete flashcards
- **Unit Organization**: Organize flashcards by units
- **SQLite Database**: Lightweight and portable database
- **RESTful API**: Clean API endpoints for all operations
- **CORS Enabled**: Support for cross-origin requests

## 📋 Requirements

- Python 3.8+
- Flask 3.0.3
- Flask-CORS 6.0.1
- Gunicorn 21.2.0 (for production)

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd webtienganh
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python backend.py
```

The application will be available at `http://127.0.0.1:8000`

## 📁 Project Structure

```
webtienganh/
├── backend.py              # Main Flask application
├── requirements.txt        # Python dependencies
├── Procfile               # For Heroku deployment
├── .gitignore             # Git ignore rules
├── webtienganh.db         # SQLite database (auto-generated)
├── web/                   # Frontend files
│   ├── index.html
│   ├── learn.html
│   └── assets/
│       ├── css/
│       ├── js/
│       └── images/
└── docs/                  # Documentation
    ├── DATABASE_MIGRATION.md
    ├── DEPLOYMENT.md
    └── REFACTORING_SUMMARY.md
```

## 🔌 API Endpoints

### Authentication

#### Register
```http
POST /register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword"
}
```

#### Login
```http
POST /login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword"
}
```

#### Logout
```http
POST /logout
Content-Type: application/json

{
  "email": "john@example.com"
}
```

### Flashcards

#### Get Flashcards
```http
GET /flashcards?unit=1
Authorization: Bearer <token>
```

#### Add Flashcard
```http
POST /flashcards
Authorization: Bearer <token>
Content-Type: application/json

{
  "unit": 1,
  "front": "Hello",
  "back": "Xin chào"
}
```

#### Update Flashcard
```http
PUT /flashcards/<id>
Authorization: Bearer <token>
Content-Type: application/json

{
  "front": "Hello",
  "back": "Chào bạn"
}
```

#### Delete Flashcard
```http
DELETE /flashcards/<id>
Authorization: Bearer <token>
```

## 🗄️ Database Schema

### Users Table
| Column   | Type    | Description          |
|----------|---------|----------------------|
| id       | INTEGER | Primary key          |
| username | TEXT    | User's display name  |
| email    | TEXT    | User's email (unique)|
| password | TEXT    | Hashed password      |

### Sessions Table
| Column | Type    | Description              |
|--------|---------|--------------------------|
| id     | INTEGER | Primary key              |
| email  | TEXT    | User's email             |
| token  | TEXT    | Session token (unique)   |

### Flashcards Table
| Column | Type    | Description              |
|--------|---------|--------------------------|
| id     | INTEGER | Primary key              |
| email  | TEXT    | Owner's email            |
| unit   | INTEGER | Unit number              |
| front  | TEXT    | Front side of flashcard  |
| back   | TEXT    | Back side of flashcard   |

## 🚀 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions for various platforms:
- Heroku
- Railway
- Render
- PythonAnywhere
- DigitalOcean

### Quick Deploy to Heroku
```bash
heroku create your-app-name
git push heroku main
heroku open
```

## 🔒 Security Features

- ✅ Password hashing using SHA-256
- ✅ Session token-based authentication
- ✅ SQL injection protection (parameterized queries)
- ✅ CORS configuration
- ✅ User data isolation

## 📝 Development

### Run in Development Mode
```bash
python backend.py
```

### Run with Gunicorn (Production-like)
```bash
gunicorn backend:app --bind 0.0.0.0:8000
```

## 🧪 Testing

Test the API endpoints using curl:

```bash
# Register a new user
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

## 📚 Documentation

- [Database Migration](DATABASE_MIGRATION.md) - Details about the SQLite migration
- [Deployment Guide](DEPLOYMENT.md) - Comprehensive deployment instructions
- [Refactoring Summary](REFACTORING_SUMMARY.md) - Summary of code changes

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Author

Created with ❤️ for English learners

## 🙏 Acknowledgments

- Flask framework
- SQLite database
- Bootstrap for frontend styling

---

**Happy Learning! 📚✨**
