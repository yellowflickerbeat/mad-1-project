from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Quiz, UserQuizzes, Question, Subject, Chapter

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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'feb17e6b4dcc472cebac25acd17cd28d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with this application
db.init_app(app)

# Create all tables
with app.app_context():
    # Drop all tables first
    db.drop_all()
    # Create all tables
    db.create_all()
    # Initialize admin user
    init_admin()

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
    try:
        full_name = request.form['full_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        qualification = request.form['qualification']
        date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('index'))

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please use a different email.', 'error')
            return redirect(url_for('index'))

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
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Registration failed: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(session['user_id'])
    assigned_quizzes = UserQuizzes.query.filter_by(user_id=user.id).all()
    
    # Calculate statistics
    total_quizzes = len(assigned_quizzes)
    completed_quizzes = sum(1 for quiz in assigned_quizzes if quiz.completed)
    pending_quizzes = total_quizzes - completed_quizzes
    
    # Get upcoming quizzes (not completed)
    upcoming_quizzes = []
    for user_quiz in assigned_quizzes:
        if not user_quiz.completed:
            quiz = user_quiz.quiz
            subject = Subject.query.get(quiz.subject_id)
            upcoming_quizzes.append({
                'id': quiz.id,
                'title': quiz.title,
                'subject_name': subject.name if subject else 'Unknown Subject',
                'assigned_at': user_quiz.assigned_at,
                'duration': quiz.duration
            })
    
    # Get completed quizzes with scores
    completed_quizzes_list = []
    for user_quiz in assigned_quizzes:
        if user_quiz.completed:
            quiz = user_quiz.quiz
            subject = Subject.query.get(quiz.subject_id)
            completed_quizzes_list.append({
                'id': quiz.id,
                'title': quiz.title,
                'subject_name': subject.name if subject else 'Unknown Subject',
                'completed_at': user_quiz.completed_at,
                'score': user_quiz.score
            })
    
    # Sort completed quizzes by completion date (newest first)
    completed_quizzes_list.sort(key=lambda x: x['completed_at'], reverse=True)
    
    return render_template('student_dashboard.html',
                         user=user,
                         total_quizzes=total_quizzes,
                         completed_quizzes=completed_quizzes,
                         pending_quizzes=pending_quizzes,
                         upcoming_quizzes=upcoming_quizzes,
                         completed_quizzes_list=completed_quizzes_list)

@app.route('/assign_quiz', methods=['POST'])
def assign_quiz():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        quiz_id = data.get('quiz_id')

        if not user_id or not quiz_id:
            return jsonify({"message": "User ID and Quiz ID are required"}), 400

        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": f"User with ID {user_id} not found"}), 404

        # Check if quiz exists
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return jsonify({"message": f"Quiz with ID {quiz_id} not found"}), 404

        # ✅ Prevent duplicate assignments
        existing_assignment = UserQuizzes.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
        if existing_assignment:
            return jsonify({"message": "Quiz already assigned to this user!"}), 400
        
        # ✅ Assign the quiz
        new_assignment = UserQuizzes(
            user_id=user_id, 
            quiz_id=quiz_id
        )
        db.session.add(new_assignment)
        db.session.commit()

        return jsonify({"message": f"Quiz {quiz.title} successfully assigned to user {user.full_name}!"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error in assign_quiz: {str(e)}")  # For debugging
        return jsonify({"message": f"Error assigning quiz: {str(e)}"}), 500

@app.route('/student/quiz')
def student_quiz():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('index'))
    
    # Get all subjects for the filter dropdown
    subjects = Subject.query.all()
    
    # Get assigned quizzes with subject and chapter information
    assigned_quizzes = db.session.query(
        Quiz,
        Subject.name.label('subject_name'),
        Chapter.title.label('chapter_name'),
        db.func.count(Question.id).label('question_count')
    ).join(
        Chapter, Quiz.chapter_id == Chapter.id
    ).join(
        Subject, Chapter.subject_id == Subject.id
    ).join(
        Question, Quiz.id == Question.quiz_id
    ).join(
        UserQuizzes, Quiz.id == UserQuizzes.quiz_id
    ).filter(
        UserQuizzes.user_id == session['user_id']
    ).group_by(
        Quiz.id, Subject.name, Chapter.title
    ).all()

    # Format the data for the template
    quizzes = []
    for quiz, subject_name, chapter_name, question_count in assigned_quizzes:
        quizzes.append({
            'id': quiz.id,
            'title': quiz.title,
            'subject_name': subject_name,
            'chapter_name': chapter_name,
            'duration': quiz.duration,
            'question_count': question_count
        })

    return render_template('student_quiz.html', assigned_quizzes=quizzes, subjects=subjects)

@app.route('/admin_quiz')
def admin_quiz():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    subjects = Subject.query.all()
    quizzes = Quiz.query.all()
    
    # Get all users with their average performance
    users = User.query.filter_by(role='student').all()
    user_performance = {}
    
    for user in users:
        # Get all completed quizzes for this user
        completed_quizzes = UserQuizzes.query.filter_by(user_id=user.id, completed=True).all()
        if completed_quizzes:
            # Calculate average score
            total_score = sum(quiz.score for quiz in completed_quizzes)
            average_score = total_score / len(completed_quizzes)
            user_performance[user.id] = round(average_score, 1)
        else:
            user_performance[user.id] = 0
    
    return render_template('admin_quiz.html', 
                         subjects=subjects, 
                         quizzes=quizzes,
                         user_performance=user_performance)

@app.route('/stats')
def stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('stats.html')

@app.route('/admin_users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    # Get all users with their average performance
    users = User.query.all()
    user_performance = {}
    
    for user in users:
        if user.role == 'student':
            # Get all completed quizzes for this user
            completed_quizzes = UserQuizzes.query.filter_by(user_id=user.id, completed=True).all()
            if completed_quizzes:
                # Calculate average score
                total_score = sum(quiz.score for quiz in completed_quizzes)
                average_score = total_score / len(completed_quizzes)
                user_performance[user.id] = round(average_score, 1)
            else:
                user_performance[user.id] = 0
    
    quizzes = Quiz.query.all()
    return render_template('admin_users.html', users=users, quizzes=quizzes, user_performance=user_performance)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    # Get all subjects with their chapters
    subjects = Subject.query.all()
    subjects_data = []
    
    for subject in subjects:
        chapters = Chapter.query.filter_by(subject_id=subject.id).order_by(Chapter.order).all()
        chapters_data = []
        
        for chapter in chapters:
            quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
            chapters_data.append({
                'id': chapter.id,
                'title': chapter.title,
                'description': chapter.description,
                'order': chapter.order,
                'quizzes': [{
                    'id': quiz.id,
                    'title': quiz.title,
                    'description': quiz.description,
                    'duration': quiz.duration
                } for quiz in quizzes]
            })
        
        subjects_data.append({
            'id': subject.id,
            'name': subject.name,
            'chapters': chapters_data
        })
    
    return render_template('admin_dashboard.html', subjects=subjects_data)

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

    try:
        data = request.get_json()
        quiz_id = data.get('quiz_id')
        title = data.get('title')
        description = data.get('description')

        if not all([quiz_id, title]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return jsonify({"success": False, "message": "Quiz not found"}), 404

        quiz.title = title
        quiz.description = description
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Quiz updated successfully",
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "subject_id": quiz.subject_id
            }
        })
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

@app.route('/get_quiz/<int:quiz_id>')
def get_quiz(quiz_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        subject = Subject.query.get(quiz.subject_id)
        questions = Question.query.filter_by(quiz_id=quiz_id).all()
        
        return jsonify({
            "success": True,
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "subject_name": subject.name if subject else "Unknown Subject",
                "subject_id": quiz.subject_id,
                "question_count": len(questions),
                "question_ids": [q.id for q in questions],
                "duration": quiz.duration
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/create_subject', methods=['POST'])
def create_subject():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({"success": False, "message": "Subject name is required"}), 400

    try:
        new_subject = Subject(
            name=name,
            description=description
        )
        db.session.add(new_subject)
        db.session.commit()
        return jsonify({"success": True, "message": "Subject created successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/create_quiz', methods=['POST'])
def create_quiz():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        subject_id = data.get('subject_id')
        chapter_id = data.get('chapter_id')
        title = data.get('title')
        description = data.get('description')
        duration = data.get('duration')  # Duration in minutes

        if not all([subject_id, chapter_id, title, duration]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        new_quiz = Quiz(
            title=title,
            description=description,
            subject_id=subject_id,
            chapter_id=chapter_id,
            duration=duration
        )
        db.session.add(new_quiz)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Quiz created successfully",
            "quiz": {
                "id": new_quiz.id,
                "title": new_quiz.title,
                "description": new_quiz.description,
                "subject_id": new_quiz.subject_id,
                "chapter_id": new_quiz.chapter_id,
                "duration": new_quiz.duration
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/take_quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    # Check if the quiz is assigned to the student
    user_quiz = UserQuizzes.query.filter_by(user_id=session['user_id'], quiz_id=quiz_id).first()
    if not user_quiz:
        flash('Quiz not found or not assigned to you.', 'error')
        return redirect(url_for('student_quiz'))
    
    # Get quiz with its questions
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.questions:
        flash('No questions available for this quiz.', 'error')
        return redirect(url_for('student_quiz'))
    
    return render_template('take_quiz.html',
                         quiz=quiz,
                         subject_name=quiz.subject.name if quiz.subject else "Unknown Subject",
                         questions=quiz.questions,
                         current_question=1,
                         total_questions=len(quiz.questions))

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_quiz = UserQuizzes.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    
    if not user_quiz:
        flash('Quiz not found or not assigned to you.', 'error')
        return redirect(url_for('student_quiz'))
    
    if user_quiz.completed:
        flash('You have already completed this quiz.', 'error')
        return redirect(url_for('student_quiz'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.questions:
        flash('No questions available for this quiz.', 'error')
        return redirect(url_for('student_quiz'))
    
    # Store answers and calculate score
    answers = {}
    correct_answers = 0
    question_results = []
    
    for question in quiz.questions:
        answer_key = f'answer_{question.id}'
        if answer_key not in request.form:
            flash('Please answer all questions.', 'error')
            return redirect(url_for('take_quiz', quiz_id=quiz_id))
        
        selected_answer = int(request.form[answer_key])
        is_correct = selected_answer == question.correct_answer
        
        # Store detailed information about each answer
        answers[str(question.id)] = {
            'selected_answer': selected_answer,
            'correct_answer': question.correct_answer,
            'is_correct': is_correct,
            'question_title': question.title,
            'options': question.options
        }
        
        if is_correct:
            correct_answers += 1
            
        question_results.append({
            'question_id': question.id,
            'is_correct': is_correct
        })
    
    # Calculate score and accuracy metrics
    total_questions = len(quiz.questions)
    score = (correct_answers / total_questions) * 100
    accuracy_data = {
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'score_percentage': score,
        'question_results': question_results
    }
    
    # Update user quiz record
    user_quiz.completed = True
    user_quiz.completed_at = datetime.utcnow()
    user_quiz.score = score
    user_quiz.answers = answers
    user_quiz.accuracy_data = accuracy_data
    
    db.session.commit()
    
    flash(f'Quiz submitted successfully! Your score: {score:.1f}%', 'success')
    return redirect(url_for('student_quiz'))

@app.route('/admin/quiz_results')
def admin_quiz_results():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    # Get all completed quizzes with user information
    completed_quizzes = UserQuizzes.query.filter_by(completed=True).all()
    
    # Organize the data for display
    quiz_results = []
    for user_quiz in completed_quizzes:
        quiz = user_quiz.quiz  # Get the associated quiz
        result = {
            'student_name': user_quiz.user.full_name,
            'quiz_title': quiz.title,
            'subject_name': quiz.subject.name,
            'completed_at': user_quiz.completed_at,
            'score': user_quiz.score,
            'total_questions': len(quiz.questions),
            'correct_answers': sum(1 for q in user_quiz.accuracy_data['question_results'] if q['is_correct']) if user_quiz.accuracy_data else 0,
            'quiz_id': quiz.id,
            'user_quiz_id': user_quiz.id,
            'duration': quiz.duration
        }
        quiz_results.append(result)
    
    # Sort by completion date (newest first)
    quiz_results.sort(key=lambda x: x['completed_at'], reverse=True)
    
    return render_template('admin_quiz_results.html', quiz_results=quiz_results)

@app.route('/admin/quiz_result_detail/<int:user_quiz_id>')
def admin_quiz_result_detail(user_quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    user_quiz = UserQuizzes.query.get_or_404(user_quiz_id)
    
    # Get detailed information about the quiz attempt
    quiz_detail = {
        'student_name': user_quiz.user.full_name,
        'quiz_title': user_quiz.quiz.title,
        'subject_name': user_quiz.quiz.subject.name,
        'completed_at': user_quiz.completed_at,
        'score': user_quiz.score,
        'answers': user_quiz.answers,
        'accuracy_data': user_quiz.accuracy_data
    }
    
    return render_template('admin_quiz_result_detail.html', quiz_detail=quiz_detail)

@app.route('/create_chapter', methods=['POST'])
def create_chapter():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        subject_id = data.get('subject_id')
        title = data.get('title')
        description = data.get('description')
        order = data.get('order')

        if not all([subject_id, title, order]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        new_chapter = Chapter(
            title=title,
            description=description,
            subject_id=subject_id,
            order=order
        )
        db.session.add(new_chapter)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Chapter created successfully",
            "chapter": {
                "id": new_chapter.id,
                "title": new_chapter.title,
                "description": new_chapter.description,
                "subject_id": new_chapter.subject_id,
                "order": new_chapter.order
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_chapter/<int:chapter_id>', methods=['DELETE'])
def delete_chapter(chapter_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        chapter = Chapter.query.get_or_404(chapter_id)
        db.session.delete(chapter)
        db.session.commit()
        return jsonify({"success": True, "message": "Chapter deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/edit_chapter/<int:chapter_id>', methods=['PUT'])
def edit_chapter(chapter_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        chapter = Chapter.query.get_or_404(chapter_id)
        data = request.get_json()
        
        chapter.title = data.get('title', chapter.title)
        chapter.description = data.get('description', chapter.description)
        chapter.order = data.get('order', chapter.order)
        
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Chapter updated successfully",
            "chapter": {
                "id": chapter.id,
                "title": chapter.title,
                "description": chapter.description,
                "subject_id": chapter.subject_id,
                "order": chapter.order
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/get_chapters/<int:subject_id>')
def get_chapters(subject_id):
    try:
        chapters = Chapter.query.filter_by(subject_id=subject_id).order_by(Chapter.order).all()
        return jsonify({
            'success': True,
            'chapters': [{
                'id': chapter.id,
                'title': chapter.title
            } for chapter in chapters]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/delete_user', methods=['POST'])
def delete_user():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if user.is_admin:
        return jsonify({'success': False, 'message': 'Cannot delete admin users'}), 400
    
    try:
        # Delete user's quiz attempts
        UserQuizzes.query.filter_by(user_id=user_id).delete()
        # Delete user's assignments
        UserAssignments.query.filter_by(user_id=user_id).delete()
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)