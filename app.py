from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Quiz, UserQuizzes, Question

app = Flask(__name__)
app.config['SECRET_KEY'] = 'feb17e6b4dcc472cebac25acd17cd28d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with this application
db.init_app(app)

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

@app.route('/register', methods=['POST'])
def register():
    full_name = request.form['full_name']
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    qualification = request.form['qualification']
    date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()

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

@app.route('/assign_quiz', methods=['POST'])
def assign_quiz():
    data = request.get_json()
    user_id = data.get('user_id')
    quiz_id = data.get('quiz_id')

    if not user_id or not quiz_id:
        return jsonify({"message": "User ID and Quiz ID are required"}), 400

    # ✅ Prevent duplicate assignments
    existing_assignment = UserQuizzes.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if existing_assignment:
        return jsonify({"message": "Quiz already assigned to this user!"}), 400

    # ✅ Assign the quiz
    new_assignment = UserQuizzes(user_id=user_id, quiz_id=quiz_id)
    db.session.add(new_assignment)
    db.session.commit()

    return jsonify({"message": f"Quiz {quiz_id} successfully assigned to user {user_id}!"}), 200

@app.route('/student_quiz')
def student_quiz():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('index'))
    return render_template('student_quiz.html')

@app.route('/admin_quiz')
def admin_quiz():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    quizzes = Quiz.query.all()
    return render_template('admin_quiz.html', quizzes=quizzes)

@app.route('/stats')
def stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('stats.html')

@app.route('/admin_users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    users = User.query.all()
    quizzes = Quiz.query.all()
    return render_template('admin_users.html', users=users, quizzes=quizzes)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/add_question', methods=['POST'])
def add_question():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    quiz_id = data.get('quiz_id')
    title = data.get('title')
    options = data.get('options')
    correct_answer = data.get('correct_answer')

    if not all([quiz_id, title, options, correct_answer is not None]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        new_question = Question(
            quiz_id=quiz_id,
            title=title,
            options=options,
            correct_answer=correct_answer
        )
        db.session.add(new_question)
        db.session.commit()
        return jsonify({"success": True, "message": "Question added successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/edit_quiz', methods=['POST'])
def edit_quiz():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    quiz_id = data.get('quiz_id')
    title = data.get('title')
    description = data.get('description')

    if not all([quiz_id, title]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        quiz.title = title
        quiz.description = description
        db.session.commit()
        return jsonify({"success": True, "message": "Quiz updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_quiz', methods=['POST'])
def delete_quiz():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    quiz_id = data.get('quiz_id')

    if not quiz_id:
        return jsonify({"success": False, "message": "Quiz ID is required"}), 400

    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        # Delete all questions associated with the quiz
        Question.query.filter_by(quiz_id=quiz_id).delete()
        # Delete all user assignments
        UserQuizzes.query.filter_by(quiz_id=quiz_id).delete()
        # Delete the quiz
        db.session.delete(quiz)
        db.session.commit()
        return jsonify({"success": True, "message": "Quiz deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_question', methods=['POST'])
def delete_question():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    question_id = data.get('question_id')

    if not question_id:
        return jsonify({"success": False, "message": "Question ID is required"}), 400

    try:
        question = Question.query.get_or_404(question_id)
        db.session.delete(question)
        db.session.commit()
        return jsonify({"success": True, "message": "Question deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

def init_admin():
    existing_admin = User.query.filter_by(username='admin1').first()
    if not existing_admin:
        admin_password = generate_password_hash('admin')
        admin_user = User(
            username='admin1',
            password=admin_password,
            role='admin',
            full_name='Admin User',
            email='admin@gmail.com',
            qualification='N/A',
            date_of_birth=datetime.strptime("2000-01-01", '%Y-%m-%d').date()
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()  # Initialize admin user on app start
    app.run(debug=True)