from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = '887cc4f3e197194c0e3eadd34b8eb6b9'  # Securely generated secret key

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    qualification = db.Column(db.String(100))
    date_of_birth = db.Column(db.String(50))
    role = db.Column(db.String(10), default='student')  # 'student' or 'admin'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create Database
with app.app_context():
    db.create_all()

# Home Route (Redirects to login.html)
@app.route('/')
def home():
    return render_template('login.html')

# Login & Registration in One Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_type = request.form.get('form_type')  # Identifies if it's login or register
        
        if form_type == 'register':  # Registration
            full_name = request.form['full_name']
            email = request.form['email']
            password = generate_password_hash(request.form['password'], method='sha256')
            qualification = request.form['qualification']
            date_of_birth = request.form['date_of_birth']

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Try logging in.', 'warning')
                return redirect(url_for('login'))

            new_user = User(full_name=full_name, email=email, password=password, qualification=qualification, date_of_birth=date_of_birth)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! You can log in now.', 'success')
            return redirect(url_for('login'))
        
        elif form_type == 'login':  # Login
            email = request.form['username']
            password = request.form['password']
            
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.password, password):
                login_user(user)
                flash('Login successful!', 'success')
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            else:
                flash('Invalid credentials, please try again.', 'danger')

    return render_template('login.html')

# Student Dashboard (Redirect to student.html)
@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    return render_template('student.html', name=current_user.full_name)

# Admin Dashboard (Redirect to admin_student.html)
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    students = User.query.filter_by(role='student').all()
    return render_template('admin_student.html', students=students)

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

'''app.route('/init_db')
def init_db():
    with app.app_context():
        db.create_all()
        return "Database Initialized!"'''

if __name__ == '__main__':
    app.run(debug=True)
