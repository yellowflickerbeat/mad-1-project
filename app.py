from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'feb17e6b4dcc472cebac25acd17cd28d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    qualification = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    user = User.query.filter_by(username=username, role=role).first()
    
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['role'] = user.role
        
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    return "Invalid credentials", 401

from datetime import datetime

@app.route('/register', methods=['POST'])
def register():
    full_name = request.form['full_name']
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    qualification = request.form['qualification']
    date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()  # Convert to date object

    hashed_password = generate_password_hash(password)
    
    new_user = User(
        full_name=full_name, 
        email=email, 
        username=username, 
        password=hashed_password,
        role='student',
        qualification=qualification,
        date_of_birth=date_of_birth
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return redirect(url_for('index'))


@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('index'))
    return render_template('student_dashboard.html')

@app.route('/student_quiz')
def student_quiz():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('index'))
    return render_template('student_quiz.html')

# Add this route to your existing app.py

@app.route('/admin_quiz')
def admin_quiz():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_quiz.html')

@app.route('/stats')
def stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('stats.html')

def admin_student():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_student.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_dashboard.html')

@app.route('/admin_student')
def admin_student():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_student.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def init_admin():
    existing_admin = User.query.filter_by(username='admin1').first()
    if not existing_admin:
        admin_password = generate_password_hash('admin')
        admin_user = User(
            username='admin1', 
            password=admin_password, 
            role='admin',
            full_name='Admin User',
            email='admin@gmail.com'
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()
    app.run(debug=True)