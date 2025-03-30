from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    qualification = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)

# Subject Model
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='subject', lazy=True)
    chapters = db.relationship('Chapter', backref='subject', lazy=True, cascade='all, delete-orphan')

# Chapter Model
class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)  # For maintaining chapter order
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Quiz
    quizzes = db.relationship('Quiz', backref='chapter', lazy=True, cascade='all, delete-orphan')

# Quiz Model
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')

# UserQuizzes Model (Many-to-Many)
class UserQuizzes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    score = db.Column(db.Float)
    answers = db.Column(db.JSON)  # Stores detailed answer information
    accuracy_data = db.Column(db.JSON)  # Stores accuracy metrics and question results

    user = db.relationship('User', backref=db.backref('assigned_quizzes', lazy=True))
    quiz = db.relationship('Quiz', backref=db.backref('assigned_to', lazy=True))

# Question Model
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    options = db.Column(db.JSON, nullable=False)  # Store options as JSON array
    correct_answer = db.Column(db.Integer, nullable=False)  # Index of correct answer in options array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)