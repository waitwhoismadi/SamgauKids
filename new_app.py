from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid
from datetime import datetime, date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///education_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

from database import db
db.init_app(app)

from models import User, Parent, Center, Teacher, Child, Category, Program, Schedule, Enrollment, Attendance
from services import GeocodingService

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            if role and session.get('user_role') != role:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def save_uploaded_file(file, folder='general'):
    if file and file.filename:
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        return f"{folder}/{filename}"
    return None

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/register')
def register_choice():
    return render_template('auth/register_choice.html')

@app.route('/register/parent', methods=['GET', 'POST'])
def register_parent():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not all([name, email, password]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register_parent.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('auth/register_parent.html')
        
        try:
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                name=name,
                phone=phone,
                role='parent'
            )
            db.session.add(user)
            db.session.flush()
            
            parent = Parent(
                user_id=user.id,
                address=address
            )
            db.session.add(parent)
            db.session.commit()
            
            flash(f'Welcome {name}! Your parent account has been created successfully.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register_parent.html')
    
    return render_template('auth/register_parent.html')

@app.route('/register/center', methods=['GET', 'POST'])
def register_center():
    if request.method == 'POST':
        center_name = request.form.get('center_name')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        description = request.form.get('description')
        
        if not all([center_name, name, email, password, address]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register_center.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('auth/register_center.html')
        
        try:
            geocoding_service = GeocodingService()
            coordinates = geocoding_service.geocode_address(address, "Astana", "Kazakhstan")
            
            if not coordinates:
                flash('Could not locate the address. Please provide a more specific address in Astana.', 'warning')
                latitude, longitude = None, None
            else:
                latitude, longitude = coordinates
                flash(f'Address located successfully at coordinates: {latitude:.4f}, {longitude:.4f}', 'info')
            
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                name=name,
                phone=phone,
                role='center'
            )
            db.session.add(user)
            db.session.flush()
            
            center = Center(
                user_id=user.id,
                center_name=center_name,
                description=description,
                address=address,
                latitude=latitude,
                longitude=longitude
            )
            db.session.add(center)
            db.session.commit()
            
            flash(f'Welcome {center_name}! Your center has been registered successfully. Your teacher invite code is: {center.invite_code}', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register_center.html')
    
    return render_template('auth/register_center.html')

@app.route('/register/teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        invite_code = request.form.get('invite_code')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        specialization = request.form.get('specialization')
        bio = request.form.get('bio')
        
        if not all([invite_code, name, email, password]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register_teacher.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('auth/register_teacher.html')
        
        center = Center.query.filter_by(invite_code=invite_code.upper()).first()
        if not center:
            flash('Invalid invite code. Please check with your education center.', 'danger')
            return render_template('auth/register_teacher.html')
        
        try:
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                name=name,
                phone=phone,
                role='teacher'
            )
            db.session.add(user)
            db.session.flush()
            
            teacher = Teacher(
                user_id=user.id,
                center_id=center.id,
                specialization=specialization,
                bio=bio
            )
            db.session.add(teacher)
            db.session.commit()
            
            flash(f'Welcome {name}! You have successfully joined {center.center_name} as a teacher.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register_teacher.html')
    
    return render_template('auth/register_teacher.html')

@app.route('/dashboard')
@login_required()
def dashboard():
    role = session.get('user_role')
    
    if role == 'parent':
        return redirect(url_for('parent_dashboard'))
    elif role == 'center':
        return redirect(url_for('center_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        flash('Invalid user role', 'danger')
        return redirect(url_for('logout'))

@app.route('/parent/dashboard')
@login_required(role='parent')
def parent_dashboard():
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    centers = Center.query.all()
    children = Child.query.filter_by(parent_id=parent.id).all() if parent else []
    
    categories = Category.query.filter_by(parent_id=None).all() 
    
    map_centers = [center for center in centers if center.latitude and center.longitude]
    
    return render_template('dashboards/parent_dashboard.html', 
                         parent=parent, 
                         centers=centers, 
                         children=children,
                         categories=categories,
                         map_centers=map_centers)

@app.route('/parent/children')
@login_required(role='parent')
def manage_children():
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    children = Child.query.filter_by(parent_id=parent.id).all() if parent else []
    
    return render_template('parent/children.html', children=children)

@app.route('/parent/children/add', methods=['GET', 'POST'])
@login_required(role='parent')
def add_child():
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    
    if request.method == 'POST':
        name = request.form.get('name')
        birth_date_str = request.form.get('birth_date')
        grade = request.form.get('grade')
        notes = request.form.get('notes')
        
        if not name:
            flash('Child name is required.', 'danger')
            return render_template('parent/add_child.html')
        
        birth_date = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid birth date format.', 'danger')
                return render_template('parent/add_child.html')
        
        photo_url = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                photo_url = save_uploaded_file(file, 'children')
        
        try:
            child = Child(
                parent_id=parent.id,
                name=name,
                birth_date=birth_date,
                grade=grade,
                notes=notes,
                photo_url=photo_url
            )
            
            db.session.add(child)
            db.session.commit()
            
            flash(f'{child.name} has been added successfully!', 'success')
            return redirect(url_for('manage_children'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding child. Please try again.', 'danger')
    
    return render_template('parent/add_child.html')

@app.route('/parent/children/<int:child_id>/edit', methods=['GET', 'POST'])
@login_required(role='parent')
def edit_child(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        flash('Child not found.', 'danger')
        return redirect(url_for('manage_children'))
    
    if request.method == 'POST':
        child.name = request.form.get('name')
        child.grade = request.form.get('grade')
        child.notes = request.form.get('notes')
        
        birth_date_str = request.form.get('birth_date')
        if birth_date_str:
            try:
                child.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid birth date format.', 'danger')
                return render_template('parent/edit_child.html', child=child)
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                child.photo_url = save_uploaded_file(file, 'children')
        
        try:
            db.session.commit()
            flash(f'{child.name} updated successfully!', 'success')
            return redirect(url_for('manage_children'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating child. Please try again.', 'danger')
    
    return render_template('parent/edit_child.html', child=child)

@app.route('/parent/children/<int:child_id>/delete', methods=['POST'])
@login_required(role='parent')
def delete_child(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        flash('Child not found.', 'danger')
        return redirect(url_for('manage_children'))
    
    try:
        active_enrollments = Enrollment.query.filter_by(child_id=child.id, status='active').count()
        if active_enrollments > 0:
            flash(f'Cannot delete {child.name}. Please cancel all active enrollments first.', 'danger')
            return redirect(url_for('manage_children'))
        
        child_name = child.name
        db.session.delete(child)
        db.session.commit()
        flash(f'{child_name} has been removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting child. Please try again.', 'danger')
    
    return redirect(url_for('manage_children'))

@app.route('/enroll/<int:schedule_id>/<int:child_id>', methods=['POST'])
@login_required(role='parent')
def enroll_child(schedule_id, child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    schedule = Schedule.query.get_or_404(schedule_id)
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    existing = Enrollment.query.filter_by(
        child_id=child_id, 
        schedule_id=schedule_id,
        status='active'
    ).first()
    
    if existing:
        return jsonify({'error': 'Child is already enrolled in this class'}), 400
    
    if child.birth_date:
        child_age = date.today().year - child.birth_date.year
        if schedule.program.min_age and child_age < schedule.program.min_age:
            return jsonify({'error': f'Child is too young for this program (minimum age: {schedule.program.min_age})'}), 400
        if schedule.program.max_age and child_age > schedule.program.max_age:
            return jsonify({'error': f'Child is too old for this program (maximum age: {schedule.program.max_age})'}), 400
    
    current_enrollments = Enrollment.query.filter_by(
        schedule_id=schedule_id,
        status='active'
    ).count()
    
    if current_enrollments >= schedule.max_students:
        return jsonify({'error': 'Class is full'}), 400
    
    try:
        enrollment = Enrollment(
            child_id=child_id,
            schedule_id=schedule_id,
            status='active'
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{child.name} has been enrolled in {schedule.program.name}!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Enrollment failed. Please try again.'}), 500

@app.route('/api/centers')
def api_centers():
    category_id = request.args.get('category_id')
    search_query = request.args.get('search', '')
    
    query = Center.query
    
    if category_id:
        query = query.join(Program).join(Category).filter(
            Category.id == category_id
        ).distinct()
    
    if search_query:
        query = query.filter(
            Center.center_name.contains(search_query) |
            Center.description.contains(search_query) |
            Center.address.contains(search_query)
        )
    
    centers = query.all()
    
    centers_data = []
    for center in centers:
        if center.latitude and center.longitude:
            programs = Program.query.filter_by(center_id=center.id, is_active=True).all()
            
            center_data = {
                'id': center.id,
                'name': center.center_name,
                'description': center.description,
                'address': center.address,
                'latitude': center.latitude,
                'longitude': center.longitude,
                'phone': center.user.phone,
                'programs_count': len(programs),
                'teachers_count': len(center.teachers),
                'programs': [
                    {
                        'id': program.id,
                        'name': program.name,
                        'category': program.category.name,
                        'category_color': program.category.color,
                        'category_icon': program.category.icon,
                        'price': program.get_price_display(),
                        'age_range': program.get_age_range()
                    }
                    for program in programs[:3] 
                ]
            }
            centers_data.append(center_data)
    
    return jsonify(centers_data)

@app.route('/api/available-programs/<int:child_id>')
@login_required(role='parent')
def available_programs(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    child_age = None
    if child.birth_date:
        child_age = date.today().year - child.birth_date.year
    
    schedules = Schedule.query.filter_by(is_active=True).all()
    
    available_programs = []
    for schedule in schedules:
        existing = Enrollment.query.filter_by(
            child_id=child_id,
            schedule_id=schedule.id,
            status='active'
        ).first()
        
        if existing:
            continue
        
        if child_age:
            if schedule.program.min_age and child_age < schedule.program.min_age:
                continue
            if schedule.program.max_age and child_age > schedule.program.max_age:
                continue
        
        current_enrollments = Enrollment.query.filter_by(
            schedule_id=schedule.id,
            status='active'
        ).count()
        
        if current_enrollments >= schedule.max_students:
            continue
        
        program_data = {
            'id': schedule.program.id,
            'name': schedule.program.name,
            'short_description': schedule.program.short_description,
            'center_name': schedule.program.center.center_name,
            'category_icon': schedule.program.category.icon,
            'category_color': schedule.program.category.color,
            'price_display': schedule.program.get_price_display(),
            'schedules': [{
                'id': schedule.id,
                'day_name': schedule.get_day_name(),
                'time_range': schedule.get_time_range()
            }]
        }
        
        available_programs.append(program_data)
    
    return jsonify({'programs': available_programs})

@app.route('/api/geocode')
def api_geocode():
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address parameter required'}), 400
    
    geocoding_service = GeocodingService()
    coordinates = geocoding_service.geocode_address(address, "Astana", "Kazakhstan")
    
    if coordinates:
        return jsonify({
            'latitude': coordinates[0],
            'longitude': coordinates[1],
            'success': True
        })
    else:
        return jsonify({
            'error': 'Address not found',
            'success': False
        }), 404

@app.route('/api/distance')
def api_distance():
    try:
        lat1 = float(request.args.get('lat1'))
        lon1 = float(request.args.get('lon1'))
        lat2 = float(request.args.get('lat2'))
        lon2 = float(request.args.get('lon2'))
        
        geocoding_service = GeocodingService()
        distance = geocoding_service.get_distance(lat1, lon1, lat2, lon2)
        
        return jsonify({
            'distance_km': round(distance, 2),
            'distance_text': f"{distance:.1f} km"
        })
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid coordinates'}), 400

@app.route('/center/dashboard')
@login_required(role='center')
def center_dashboard():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    teachers = Teacher.query.filter_by(center_id=center.id).all() if center else []
    programs = Program.query.filter_by(center_id=center.id).all() if center else []
    schedules = Schedule.query.join(Program).filter(Program.center_id == center.id).all() if center else []
    
    total_students = 0
    if center:
        total_students = db.session.query(Enrollment).join(Schedule).join(Program).filter(
            Program.center_id == center.id,
            Enrollment.status == 'active'
        ).count()
    
    stats = {
        'programs': len(programs),
        'teachers': len(teachers),
        'students': total_students,
        'classes': len(schedules)
    }
    
    return render_template('dashboards/center_dashboard.html', 
                         center=center, 
                         teachers=teachers, 
                         programs=programs,
                         schedules=schedules[:5],
                         stats=stats)

@app.route('/teacher/dashboard')
@login_required(role='teacher')
def teacher_dashboard():
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    center = teacher.center if teacher else None
    schedules = Schedule.query.filter_by(teacher_id=teacher.id, is_active=True).all() if teacher else []
    
    today = date.today()
    today_weekday = today.weekday()
    today_classes = [s for s in schedules if s.day_of_week == today_weekday]
    
    total_students = 0
    if teacher:
        total_students = db.session.query(Enrollment).join(Schedule).filter(
            Schedule.teacher_id == teacher.id,
            Enrollment.status == 'active'
        ).count()
    
    stats = {
        'today_classes': len(today_classes),
        'students': total_students,
        'assigned_classes': len(schedules)
    }
    
    return render_template('dashboards/teacher_dashboard.html', 
                         teacher=teacher, 
                         center=center, 
                         schedules=schedules,
                         today_classes=today_classes,
                         stats=stats)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/center/programs')
@login_required(role='center')
def center_programs():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    programs = Program.query.filter_by(center_id=center.id).all() if center else []
    categories = Category.query.all()
    
    return render_template('center/programs.html', 
                         center=center, 
                         programs=programs,
                         categories=categories)

@app.route('/center/programs/add', methods=['GET', 'POST'])
@login_required(role='center')
def add_program():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    if request.method == 'POST':
        name = request.form.get('name')
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        short_description = request.form.get('short_description')
        price_per_month = request.form.get('price_per_month')
        price_per_session = request.form.get('price_per_session')
        duration_minutes = request.form.get('duration_minutes')
        min_age = request.form.get('min_age')
        max_age = request.form.get('max_age')
        max_students = request.form.get('max_students')
        requirements = request.form.get('requirements')
        benefits = request.form.get('benefits')
        
        if not all([name, category_id]):
            flash('Please fill in program name and select a category.', 'danger')
            return redirect(request.url)
        
        try:
            photo_url = None
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    photo_url = save_uploaded_file(file, 'programs')
            
            program = Program(
                center_id=center.id,
                category_id=int(category_id),
                name=name,
                description=description,
                short_description=short_description,
                price_per_month=float(price_per_month) if price_per_month else None,
                price_per_session=float(price_per_session) if price_per_session else None,
                duration_minutes=int(duration_minutes) if duration_minutes else None,
                min_age=int(min_age) if min_age else None,
                max_age=int(max_age) if max_age else None,
                max_students=int(max_students) if max_students else 20,
                requirements=requirements,
                benefits=benefits,
                photo_url=photo_url
            )
            
            db.session.add(program)
            db.session.commit()
            
            flash(f'Program "{name}" has been added successfully!', 'success')
            return redirect(url_for('center_programs'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the program. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('center/add_program.html', center=center, categories=categories)

@app.route('/center/programs/<int:program_id>/edit', methods=['GET', 'POST'])
@login_required(role='center')
def edit_program(program_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    program = Program.query.filter_by(id=program_id, center_id=center.id).first()
    
    if not program:
        flash('Program not found.', 'danger')
        return redirect(url_for('center_programs'))
    
    if request.method == 'POST':
        program.name = request.form.get('name')
        program.category_id = int(request.form.get('category_id'))
        program.description = request.form.get('description')
        program.short_description = request.form.get('short_description')
        
        price_per_month = request.form.get('price_per_month')
        program.price_per_month = float(price_per_month) if price_per_month else None
        
        price_per_session = request.form.get('price_per_session')
        program.price_per_session = float(price_per_session) if price_per_session else None
        
        duration_minutes = request.form.get('duration_minutes')
        program.duration_minutes = int(duration_minutes) if duration_minutes else None
        
        min_age = request.form.get('min_age')
        program.min_age = int(min_age) if min_age else None
        
        max_age = request.form.get('max_age')
        program.max_age = int(max_age) if max_age else None
        
        max_students = request.form.get('max_students')
        program.max_students = int(max_students) if max_students else 20
        
        program.requirements = request.form.get('requirements')
        program.benefits = request.form.get('benefits')
        program.is_active = bool(request.form.get('is_active'))
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                program.photo_url = save_uploaded_file(file, 'programs')
        
        try:
            db.session.commit()
            flash(f'Program "{program.name}" has been updated successfully!', 'success')
            return redirect(url_for('center_programs'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the program. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('center/edit_program.html', center=center, program=program, categories=categories)

@app.route('/center/programs/<int:program_id>/delete', methods=['POST'])
@login_required(role='center')
def delete_program(program_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    program = Program.query.filter_by(id=program_id, center_id=center.id).first()
    
    if not program:
        flash('Program not found.', 'danger')
        return redirect(url_for('center_programs'))
    
    try:
        active_enrollments = db.session.query(Enrollment).join(Schedule).filter(
            Schedule.program_id == program.id,
            Enrollment.status == 'active'
        ).count()
        
        if active_enrollments > 0:
            flash(f'Cannot delete program with {active_enrollments} active enrollments.', 'danger')
            return redirect(url_for('center_programs'))
        
        program_name = program.name
        db.session.delete(program)
        db.session.commit()
        flash(f'Program "{program_name}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the program. Please try again.', 'danger')
    
    return redirect(url_for('center_programs'))

@app.route('/center/schedules')
@login_required(role='center')
def center_schedules():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    schedules = Schedule.query.join(Program).filter(
        Program.center_id == center.id
    ).order_by(Schedule.day_of_week, Schedule.start_time).all() if center else []
    
    programs = Program.query.filter_by(center_id=center.id, is_active=True).all() if center else []
    teachers = Teacher.query.filter_by(center_id=center.id).all() if center else []
    
    return render_template('center/schedules.html', 
                         center=center, 
                         schedules=schedules,
                         programs=programs,
                         teachers=teachers)

@app.route('/center/schedules/add', methods=['GET', 'POST'])
@login_required(role='center')
def add_schedule():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    if request.method == 'POST':
        from datetime import time
        
        program_id = request.form.get('program_id')
        teacher_id = request.form.get('teacher_id')
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        max_students = request.form.get('max_students')
        room_name = request.form.get('room_name')
        notes = request.form.get('notes')
        
        if not all([program_id, teacher_id, day_of_week, start_time_str, end_time_str]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(request.url)
        
        program = Program.query.filter_by(id=program_id, center_id=center.id).first()
        teacher = Teacher.query.filter_by(id=teacher_id, center_id=center.id).first()
        
        if not program or not teacher:
            flash('Invalid program or teacher selection.', 'danger')
            return redirect(request.url)
        
        try:
            start_time = time.fromisoformat(start_time_str)
            end_time = time.fromisoformat(end_time_str)
            
            if start_time >= end_time:
                flash('End time must be after start time.', 'danger')
                return redirect(request.url)
            
            existing_schedules = Schedule.query.filter_by(
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                is_active=True
            ).all()
            
            new_schedule = Schedule(
                program_id=program_id,
                teacher_id=teacher_id,
                day_of_week=int(day_of_week),
                start_time=start_time,
                end_time=end_time,
                max_students=int(max_students) if max_students else program.max_students,
                room_name=room_name,
                notes=notes
            )
            
            for existing in existing_schedules:
                if new_schedule.conflicts_with(existing):
                    flash(f'Schedule conflicts with existing class: {existing.program.name} at {existing.get_time_range()}', 'danger')
                    return redirect(request.url)
            
            db.session.add(new_schedule)
            db.session.commit()
            
            flash(f'Class schedule created successfully for {program.name}!', 'success')
            return redirect(url_for('center_schedules'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the schedule. Please try again.', 'danger')
    
    programs = Program.query.filter_by(center_id=center.id, is_active=True).all() if center else []
    teachers = Teacher.query.filter_by(center_id=center.id).all() if center else []
    
    return render_template('center/add_schedule.html', 
                         center=center, 
                         programs=programs,
                         teachers=teachers)

@app.route('/center/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required(role='center')
def edit_schedule(schedule_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    schedule = Schedule.query.join(Program).filter(
        Schedule.id == schedule_id,
        Program.center_id == center.id
    ).first()
    
    if not schedule:
        flash('Schedule not found.', 'danger')
        return redirect(url_for('center_schedules'))
    
    if request.method == 'POST':
        from datetime import time
        
        program_id = request.form.get('program_id')
        teacher_id = request.form.get('teacher_id')
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        max_students = request.form.get('max_students')
        room_name = request.form.get('room_name')
        notes = request.form.get('notes')
        is_active = bool(request.form.get('is_active'))
        
        try:
            start_time = time.fromisoformat(start_time_str)
            end_time = time.fromisoformat(end_time_str)
            
            if start_time >= end_time:
                flash('End time must be after start time.', 'danger')
                return redirect(request.url)
            
            existing_schedules = Schedule.query.filter(
                Schedule.teacher_id == teacher_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                Schedule.id != schedule_id
            ).all()
            
            schedule.program_id = program_id
            schedule.teacher_id = teacher_id
            schedule.day_of_week = int(day_of_week)
            schedule.start_time = start_time
            schedule.end_time = end_time
            schedule.max_students = int(max_students) if max_students else schedule.program.max_students
            schedule.room_name = room_name
            schedule.notes = notes
            schedule.is_active = is_active
            
            for existing in existing_schedules:
                if schedule.conflicts_with(existing):
                    flash(f'Schedule conflicts with existing class: {existing.program.name} at {existing.get_time_range()}', 'danger')
                    return redirect(request.url)
            
            db.session.commit()
            flash('Schedule updated successfully!', 'success')
            return redirect(url_for('center_schedules'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the schedule. Please try again.', 'danger')
    
    programs = Program.query.filter_by(center_id=center.id, is_active=True).all()
    teachers = Teacher.query.filter_by(center_id=center.id).all()
    
    return render_template('center/edit_schedule.html', 
                         center=center, 
                         schedule=schedule,
                         programs=programs,
                         teachers=teachers)

@app.route('/center/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required(role='center')
def delete_schedule(schedule_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    schedule = Schedule.query.join(Program).filter(
        Schedule.id == schedule_id,
        Program.center_id == center.id
    ).first()
    
    if not schedule:
        flash('Schedule not found.', 'danger')
        return redirect(url_for('center_schedules'))
    
    try:
        active_enrollments = Enrollment.query.filter_by(
            schedule_id=schedule_id,
            status='active'
        ).count()
        
        if active_enrollments > 0:
            flash(f'Cannot delete schedule with {active_enrollments} active enrollments. Please cancel enrollments first.', 'danger')
            return redirect(url_for('center_schedules'))
        
        schedule_info = f"{schedule.program.name} - {schedule.get_day_name()} {schedule.get_time_range()}"
        db.session.delete(schedule)
        db.session.commit()
        
        flash(f'Schedule "{schedule_info}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the schedule. Please try again.', 'danger')
    
    return redirect(url_for('center_schedules'))

@app.route('/teacher/schedule')
@login_required(role='teacher')
def teacher_schedule():
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    
    schedules = Schedule.query.filter_by(
        teacher_id=teacher.id, 
        is_active=True
    ).order_by(Schedule.day_of_week, Schedule.start_time).all() if teacher else []
    
    schedule_by_day = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day_num, day_name in enumerate(days):
        schedule_by_day[day_name] = [
            s for s in schedules if s.day_of_week == day_num
        ]
    
    return render_template('teacher/schedule.html', 
                         teacher=teacher,
                         schedule_by_day=schedule_by_day,
                         days=days)

@app.route('/teacher/students')
@login_required(role='teacher')
def teacher_students():
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    
    enrollments = Enrollment.query.join(Schedule).filter(
        Schedule.teacher_id == teacher.id,
        Enrollment.status == 'active'
    ).order_by(Schedule.day_of_week, Schedule.start_time).all() if teacher else []
    
    students_by_class = {}
    for enrollment in enrollments:
        schedule = enrollment.schedule
        class_key = f"{schedule.program.name} - {schedule.get_day_name()} {schedule.get_time_range()}"
        
        if class_key not in students_by_class:
            students_by_class[class_key] = {
                'schedule': schedule,
                'students': []
            }
        
        students_by_class[class_key]['students'].append(enrollment)
    
    return render_template('teacher/students.html', 
                         teacher=teacher,
                         students_by_class=students_by_class)

@app.route('/admin/geocode-centers')
def geocode_existing_centers():
    if not app.debug:
        return "This function is only available in debug mode", 403
    
    geocoding_service = GeocodingService()
    centers = Center.query.filter(Center.latitude.is_(None)).all()
    
    updated_count = 0
    for center in centers:
        try:
            coordinates = geocoding_service.geocode_address(center.address, "Astana", "Kazakhstan")
            if coordinates:
                center.latitude, center.longitude = coordinates
                updated_count += 1
        except Exception as e:
            print(f"Error geocoding {center.center_name}: {e}")
    
    if updated_count > 0:
        db.session.commit()
        return f"Successfully geocoded {updated_count} centers"
    else:
        return "No centers updated"

def init_default_categories():
    if Category.query.count() == 0:
        sports = Category(name='Sports', description='Physical activities and sports programs', icon='bi-trophy', color='#28a745')
        arts = Category(name='Arts & Crafts', description='Creative and artistic programs', icon='bi-palette', color='#6f42c1')
        academic = Category(name='Academic', description='Educational and academic subjects', icon='bi-book', color='#007bff')
        tech = Category(name='Technology', description='Programming, robotics, and tech skills', icon='bi-cpu', color='#17a2b8')
        music = Category(name='Music', description='Musical instruments and vocal training', icon='bi-music-note', color='#fd7e14')
        language = Category(name='Languages', description='Foreign language learning', icon='bi-translate', color='#20c997')
        
        db.session.add_all([sports, arts, academic, tech, music, language])
        db.session.commit()
        
        martial_arts = Category(name='Martial Arts', parent_id=sports.id, icon='bi-person-arms-up', color='#dc3545')
        team_sports = Category(name='Team Sports', parent_id=sports.id, icon='bi-people', color='#28a745')
        individual_sports = Category(name='Individual Sports', parent_id=sports.id, icon='bi-person', color='#ffc107')
        visual_arts = Category(name='Visual Arts', parent_id=arts.id, icon='bi-brush', color='#6f42c1')
        performing_arts = Category(name='Performing Arts', parent_id=arts.id, icon='bi-mask', color='#e83e8c')
        math = Category(name='Mathematics', parent_id=academic.id, icon='bi-calculator', color='#007bff')
        science = Category(name='Science', parent_id=academic.id, icon='bi-flask', color='#17a2b8')
        
        db.session.add_all([martial_arts, team_sports, individual_sports, visual_arts, performing_arts, math, science])
        db.session.commit()
        
        boxing = Category(name='Boxing', parent_id=martial_arts.id, icon='bi-hand-fist', color='#dc3545')
        karate = Category(name='Karate', parent_id=martial_arts.id, icon='bi-person-arms-up', color='#fd7e14')
        football = Category(name='Football', parent_id=team_sports.id, icon='bi-soccer', color='#28a745')
        
        db.session.add_all([boxing, karate, football])
        db.session.commit()

@app.route('/center/enrollments')
@login_required(role='center')
def center_enrollments():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    enrollments = db.session.query(Enrollment).join(Schedule).join(Program).filter(
        Program.center_id == center.id
    ).order_by(Enrollment.created_at.desc()).all() if center else []
    
    active_enrollments = [e for e in enrollments if e.status == 'active']
    pending_enrollments = [e for e in enrollments if e.status == 'pending']
    cancelled_enrollments = [e for e in enrollments if e.status == 'cancelled']
    
    return render_template('center/enrollments.html',
                         center=center,
                         active_enrollments=active_enrollments,
                         pending_enrollments=pending_enrollments,
                         cancelled_enrollments=cancelled_enrollments)

@app.route('/center/enrollment/<int:enrollment_id>/approve', methods=['POST'])
@login_required(role='center')
def approve_enrollment(enrollment_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    enrollment = db.session.query(Enrollment).join(Schedule).join(Program).filter(
        Enrollment.id == enrollment_id,
        Program.center_id == center.id
    ).first()
    
    if not enrollment:
        return jsonify({'error': 'Enrollment not found'}), 404
    
    try:
        enrollment.status = 'active'
        enrollment.approved_by = session['user_id']
        enrollment.approved_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Enrollment approved for {enrollment.child.name}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to approve enrollment'}), 500

@app.route('/parent/enrollments')
@login_required(role='parent')
def parent_enrollments():
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    
    enrollments = db.session.query(Enrollment).join(Child).filter(
        Child.parent_id == parent.id
    ).order_by(Enrollment.created_at.desc()).all() if parent else []
    
    return render_template('parent/enrollments.html',
                         parent=parent,
                         enrollments=enrollments)

@app.route('/api/child/<int:child_id>/enrollments')
@login_required(role='parent')
def api_child_enrollments(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    enrollments_data = []
    for enrollment in child.enrollments:
        enrollment_data = {
            'id': enrollment.id,
            'program_name': enrollment.schedule.program.name,
            'center_name': enrollment.schedule.program.center.center_name,
            'schedule': enrollment.get_schedule_info(),
            'status': enrollment.status,
            'enrollment_date': enrollment.enrollment_date.strftime('%Y-%m-%d'),
            'status_display': enrollment.get_status_display(),
            'status_class': enrollment.get_status_badge_class()
        }
        enrollments_data.append(enrollment_data)
    
    return jsonify({'enrollments': enrollments_data})

@app.route('/api/center/<int:center_id>/stats')
def api_center_stats(center_id):
    center = Center.query.get_or_404(center_id)
    
    total_programs = Program.query.filter_by(center_id=center.id, is_active=True).count()
    total_teachers = Teacher.query.filter_by(center_id=center.id).count()
    total_students = db.session.query(Enrollment).join(Schedule).join(Program).filter(
        Program.center_id == center.id,
        Enrollment.status == 'active'
    ).count()
    
    recent_enrollments = db.session.query(Enrollment).join(Schedule).join(Program).filter(
        Program.center_id == center.id
    ).order_by(Enrollment.created_at.desc()).limit(5).all()
    
    recent_data = []
    for enrollment in recent_enrollments:
        recent_data.append({
            'child_name': enrollment.child.name,
            'program_name': enrollment.schedule.program.name,
            'enrollment_date': enrollment.enrollment_date.strftime('%Y-%m-%d'),
            'status': enrollment.get_status_display()
        })
    
    return jsonify({
        'total_programs': total_programs,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'recent_enrollments': recent_data
    })

@app.route('/center/profile', methods=['GET', 'POST'])
@login_required(role='center')
def center_profile():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    if request.method == 'POST':
        center.center_name = request.form.get('center_name')
        center.description = request.form.get('description')
        center.address = request.form.get('address')
        center.website = request.form.get('website')
        center.schedule_info = request.form.get('schedule_info')
        
        center.user.name = request.form.get('name')
        center.user.email = request.form.get('email')
        center.user.phone = request.form.get('phone')
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                center.photo_url = save_uploaded_file(file, 'centers')
        
        if request.form.get('address') != center.address:
            geocoding_service = GeocodingService()
            coordinates = geocoding_service.geocode_address(center.address, "Astana", "Kazakhstan")
            if coordinates:
                center.latitude, center.longitude = coordinates
                flash('Address updated and location coordinates refreshed.', 'info')
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('center_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')
    
    return render_template('center/profile.html', center=center)

@app.route('/center/regenerate-invite-code', methods=['POST'])
@login_required(role='center')
def regenerate_invite_code():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    try:
        new_code = center.generate_invite_code()
        center.invite_code = new_code
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_code': new_code
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False}), 500

@app.route('/center/teachers')
@login_required(role='center')
def center_teachers():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    teachers = Teacher.query.filter_by(center_id=center.id).all() if center else []
    
    return render_template('center/teachers.html', center=center, teachers=teachers)

@app.route('/center/teacher/<int:teacher_id>/details')
@login_required(role='center')
def teacher_details_api(teacher_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    teacher = Teacher.query.filter_by(id=teacher_id, center_id=center.id).first()
    
    if not teacher:
        return jsonify({'success': False}), 404
    
    schedules = Schedule.query.filter_by(teacher_id=teacher.id).all()
    total_students = 0
    for schedule in schedules:
        total_students += len([e for e in schedule.enrollments if e.status == 'active'])
    
    html = f"""
    <div class="row">
        <div class="col-md-6">
            <h6>Personal Information</h6>
            <p><strong>Name:</strong> {teacher.user.name}</p>
            <p><strong>Email:</strong> {teacher.user.email}</p>
            <p><strong>Phone:</strong> {teacher.user.phone or 'Not provided'}</p>
            <p><strong>Specialization:</strong> {teacher.specialization or 'Not specified'}</p>
            <p><strong>Joined:</strong> {teacher.hire_date.strftime('%B %d, %Y') if teacher.hire_date else 'Recently'}</p>
        </div>
        <div class="col-md-6">
            <h6>Teaching Statistics</h6>
            <p><strong>Classes Assigned:</strong> {len(schedules)}</p>
            <p><strong>Total Students:</strong> {total_students}</p>
            <p><strong>Active Schedules:</strong> {len([s for s in schedules if s.is_active])}</p>
        </div>
    </div>
    """
    
    if teacher.bio:
        html += f"""
        <hr>
        <h6>Bio</h6>
        <p>{teacher.bio}</p>
        """
    
    if schedules:
        html += """
        <hr>
        <h6>Current Classes</h6>
        <div class="list-group">
        """
        for schedule in schedules:
            if schedule.is_active:
                html += f"""
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{schedule.program.name}</strong>
                            <br><small>{schedule.get_day_name()} {schedule.get_time_range()}</small>
                        </div>
                        <span class="badge bg-primary">{len([e for e in schedule.enrollments if e.status == 'active'])} students</span>
                    </div>
                </div>
                """
        html += "</div>"
    
    return jsonify({'success': True, 'html': html})

@app.route('/center/teacher/<int:teacher_id>/remove', methods=['POST'])
@login_required(role='center')
def remove_teacher(teacher_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    teacher = Teacher.query.filter_by(id=teacher_id, center_id=center.id).first()
    
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404
    
    try:
        active_schedules = Schedule.query.filter_by(teacher_id=teacher.id, is_active=True).count()
        if active_schedules > 0:
            return jsonify({
                'error': f'Cannot remove teacher with {active_schedules} active class schedules. Please reassign or cancel these classes first.'
            }), 400
        
        teacher_name = teacher.user.name
        
        Schedule.query.filter_by(teacher_id=teacher.id).delete()
        
        db.session.delete(teacher)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{teacher_name} has been removed from your center.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove teacher'}), 500

@app.route('/api/child/<int:child_id>/available-programs')
@login_required(role='parent')
def get_available_programs_for_child(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    child_age = None
    if child.birth_date:
        from datetime import date
        child_age = date.today().year - child.birth_date.year
    
    schedules = Schedule.query.filter_by(is_active=True).all()
    
    available_programs = []
    processed_programs = set()
    
    for schedule in schedules:
        if schedule.program.id in processed_programs:
            continue
        
        existing = Enrollment.query.filter_by(
            child_id=child_id,
            schedule_id=schedule.id,
            status='active'
        ).first()
        
        if existing:
            continue
        
        if child_age:
            if schedule.program.min_age and child_age < schedule.program.min_age:
                continue
            if schedule.program.max_age and child_age > schedule.program.max_age:
                continue
        
        current_enrollments = Enrollment.query.filter_by(
            schedule_id=schedule.id,
            status='active'
        ).count()
        
        if current_enrollments >= schedule.max_students:
            continue
        
        program_schedules = Schedule.query.filter_by(
            program_id=schedule.program.id,
            is_active=True
        ).all()
        
        available_schedules = []
        for prog_schedule in program_schedules:
            current_count = Enrollment.query.filter_by(
                schedule_id=prog_schedule.id,
                status='active'
            ).count()
            
            if current_count < prog_schedule.max_students:
                available_schedules.append({
                    'id': prog_schedule.id,
                    'day_name': prog_schedule.get_day_name(),
                    'time_range': prog_schedule.get_time_range(),
                    'teacher_name': prog_schedule.teacher.user.name,
                    'room_name': prog_schedule.room_name,
                    'available_spots': prog_schedule.max_students - current_count,
                    'max_students': prog_schedule.max_students
                })
        
        if available_schedules:
            program_data = {
                'id': schedule.program.id,
                'name': schedule.program.name,
                'short_description': schedule.program.short_description,
                'description': schedule.program.description,
                'center_name': schedule.program.center.center_name,
                'center_id': schedule.program.center.id,
                'category_icon': schedule.program.category.icon,
                'category_color': schedule.program.category.color,
                'category_name': schedule.program.category.name,
                'price_display': schedule.program.get_price_display(),
                'age_range': schedule.program.get_age_range(),
                'duration_minutes': schedule.program.duration_minutes,
                'schedules': available_schedules
            }
            
            available_programs.append(program_data)
            processed_programs.add(schedule.program.id)
    
    return jsonify({'programs': available_programs})

@app.route('/api/enroll', methods=['POST'])
@login_required(role='parent')
def api_enroll_child():
    data = request.get_json()
    child_id = data.get('child_id')
    schedule_id = data.get('schedule_id')
    
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    schedule = Schedule.query.get(schedule_id)
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    existing = Enrollment.query.filter_by(
        child_id=child_id,
        schedule_id=schedule_id,
        status__in=['active', 'pending']
    ).first()
    
    if existing:
        return jsonify({'error': 'Child is already enrolled or has a pending enrollment in this class'}), 400
    
    if child.birth_date:
        child_age = date.today().year - child.birth_date.year
        if schedule.program.min_age and child_age < schedule.program.min_age:
            return jsonify({'error': f'Child is too young for this program (minimum age: {schedule.program.min_age})'}), 400
        if schedule.program.max_age and child_age > schedule.program.max_age:
            return jsonify({'error': f'Child is too old for this program (maximum age: {schedule.program.max_age})'}), 400
    
    current_enrollments = Enrollment.query.filter_by(
        schedule_id=schedule_id,
        status__in=['active', 'pending']
    ).count()
    
    if current_enrollments >= schedule.max_students:
        return jsonify({'error': 'Class is full'}), 400
    
    try:
        enrollment = Enrollment(
            child_id=child_id,
            schedule_id=schedule_id,
            status='pending',  
            created_by=session['user_id'],
            monthly_fee=schedule.program.price_per_month,
            session_fee=schedule.program.price_per_session
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{child.name} has been enrolled in {schedule.program.name}! Your enrollment is pending center approval.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Enrollment failed. Please try again.'}), 500

@app.route('/teacher/student/<int:child_id>/details')
@login_required(role='teacher')
def student_details_api(child_id):
    """Get student details for teacher"""
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    
    enrollment = Enrollment.query.join(Schedule).filter(
        Schedule.teacher_id == teacher.id,
        Enrollment.child_id == child_id,
        Enrollment.status == 'active'
    ).first()
    
    if not enrollment:
        return jsonify({'success': False}), 404
    
    child = enrollment.child
    
    html = f"""
    <div class="row">
        <div class="col-md-6">
            <h6>Student Information</h6>
            <p><strong>Name:</strong> {child.name}</p>
            <p><strong>Age:</strong> {child.get_age_display()}</p>
            <p><strong>Grade:</strong> {child.grade or 'Not specified'}</p>
            <p><strong>Enrolled:</strong> {enrollment.enrollment_date.strftime('%B %d, %Y')}</p>
        </div>
        <div class="col-md-6">
            <h6>Parent Contact</h6>
            <p><strong>Parent:</strong> {child.parent.user.name}</p>
            <p><strong>Email:</strong> {child.parent.user.email}</p>
            <p><strong>Phone:</strong> {child.parent.user.phone or 'Not provided'}</p>
        </div>
    </div>
    """
    
    if child.notes:
        html += f"""
        <hr>
        <h6>Important Notes</h6>
        <div class="alert alert-info">
            {child.notes}
        </div>
        """
    attendance_records = enrollment.attendance_records
    if attendance_records:
        present_count = len([a for a in attendance_records if a.status == 'present'])
        total_count = len(attendance_records)
        attendance_rate = (present_count / total_count * 100) if total_count > 0 else 0
        
        html += f"""
        <hr>
        <h6>Attendance Summary</h6>
        <div class="row">
            <div class="col-md-3">
                <div class="text-center">
                    <div class="h4 text-success">{present_count}</div>
                    <small>Present</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <div class="h4 text-danger">{len([a for a in attendance_records if a.status == 'absent'])}</div>
                    <small>Absent</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <div class="h4 text-warning">{len([a for a in attendance_records if a.status == 'late'])}</div>
                    <small>Late</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <div class="h4 text-primary">{attendance_rate:.0f}%</div>
                    <small>Rate</small>
                </div>
            </div>
        </div>
        """
    
    return jsonify({'success': True, 'html': html})

@app.route('/teacher/parent/<int:parent_id>/contact')
@login_required(role='teacher')
def parent_contact_api(parent_id):
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    parent = Parent.query.get(parent_id)
    
    if not parent:
        return jsonify({'success': False}), 404
    
    has_access = False
    for child in parent.children:
        enrollment = Enrollment.query.join(Schedule).filter(
            Schedule.teacher_id == teacher.id,
            Enrollment.child_id == child.id,
            Enrollment.status == 'active'
        ).first()
        if enrollment:
            has_access = True
            break
    
    if not has_access:
        return jsonify({'success': False}), 403
    
    html = f"""
    <div class="text-center mb-3">
        <h5>{parent.user.name}</h5>
        <p class="text-muted">Parent Contact Information</p>
    </div>
    
    <div class="row g-3">
        <div class="col-12">
            <div class="d-flex align-items-center p-3 bg-light rounded">
                <i class="bi bi-envelope-fill text-primary me-3 fs-4"></i>
                <div>
                    <div class="fw-bold">Email</div>
                    <div>{parent.user.email}</div>
                </div>
            </div>
        </div>
        
        {f'''
        <div class="col-12">
            <div class="d-flex align-items-center p-3 bg-light rounded">
                <i class="bi bi-telephone-fill text-success me-3 fs-4"></i>
                <div>
                    <div class="fw-bold">Phone</div>
                    <div>{parent.user.phone}</div>
                </div>
            </div>
        </div>
        ''' if parent.user.phone else ''}
        
        {f'''
        <div class="col-12">
            <div class="d-flex align-items-center p-3 bg-light rounded">
                <i class="bi bi-geo-alt-fill text-info me-3 fs-4"></i>
                <div>
                    <div class="fw-bold">Address</div>
                    <div>{parent.address}</div>
                </div>
            </div>
        </div>
        ''' if parent.address else ''}
    </div>
    
    <div class="mt-3 d-grid gap-2">
        {f'<a href="mailto:{parent.user.email}" class="btn btn-primary"><i class="bi bi-envelope me-2"></i>Send Email</a>' if parent.user.email else ''}
        {f'<a href="tel:{parent.user.phone}" class="btn btn-success"><i class="bi bi-telephone me-2"></i>Call Parent</a>' if parent.user.phone else ''}
    </div>
    """
    
    return jsonify({'success': True, 'html': html})

@app.route('/teacher/attendance/mark', methods=['POST'])
@login_required(role='teacher')
def mark_attendance():
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    data = request.get_json()
    
    enrollment_id = data.get('enrollment_id')
    attendance_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
    status = data.get('status')
    notes = data.get('notes', '')
    
    enrollment = Enrollment.query.join(Schedule).filter(
        Schedule.teacher_id == teacher.id,
        Enrollment.id == enrollment_id,
        Enrollment.status == 'active'
    ).first()
    
    if not enrollment:
        return jsonify({'error': 'Enrollment not found or access denied'}), 404
    
    existing = Attendance.query.filter_by(
        enrollment_id=enrollment_id,
        class_date=attendance_date
    ).first()
    
    try:
        if existing:
            existing.status = status
            existing.notes = notes
        else:
            attendance = Attendance(
                enrollment_id=enrollment_id,
                class_date=attendance_date,
                status=status,
                notes=notes
            )
            db.session.add(attendance)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to mark attendance'}), 500

@app.route('/program/<int:program_id>')
def view_program(program_id):
    """Public program detail view"""
    program = Program.query.get_or_404(program_id)
    if not program.is_active:
        flash('This program is currently not available.', 'warning')
        return redirect(url_for('index'))
    
    schedules = Schedule.query.filter_by(program_id=program.id, is_active=True).all()
    
    schedule_availability = []
    for schedule in schedules:
        current_enrollments = Enrollment.query.filter_by(
            schedule_id=schedule.id,
            status__in=['active', 'pending']
        ).count()
        
        schedule_availability.append({
            'schedule': schedule,
            'available_spots': schedule.max_students - current_enrollments,
            'is_full': current_enrollments >= schedule.max_students
        })
    
    return render_template('public/program_detail.html', 
                         program=program, 
                         schedule_availability=schedule_availability)

@app.route('/center/<int:center_id>')
def view_center(center_id):
    """Enhanced public center profile view"""
    center = Center.query.get_or_404(center_id)
    programs = Program.query.filter_by(center_id=center.id, is_active=True).all()
    teachers = Teacher.query.filter_by(center_id=center.id).all()
    
    active_schedules_count = 0
    unique_categories = set()
    total_students = 0
    
    for program in programs:
        for schedule in program.schedules:
            if schedule.is_active:
                active_schedules_count += 1
                total_students += len([e for e in schedule.enrollments if e.status == 'active'])
        
        unique_categories.add(program.category.id)
    
    stats = {
        'programs': len(programs),
        'teachers': len(teachers),
        'active_schedules': active_schedules_count,
        'categories': len(unique_categories),
        'students': total_students
    }
    
    return render_template('public/center_profile.html', 
                         center=center, 
                         programs=programs,
                         teachers=teachers,
                         stats=stats)


@app.route('/api/program/<int:program_id>/details')
def api_program_details(program_id):
    program = Program.query.get_or_404(program_id)
    
    if not program.is_active:
        return jsonify({'success': False, 'error': 'Program not available'}), 404
    
    schedules = Schedule.query.filter_by(program_id=program.id, is_active=True).all()
    
    schedule_data = []
    for schedule in schedules:
        current_enrollments = Enrollment.query.filter_by(
            schedule_id=schedule.id,
            status__in=['active', 'pending']
        ).count()
        
        schedule_data.append({
            'id': schedule.id,
            'day_name': schedule.get_day_name(),
            'time_range': schedule.get_time_range(),
            'teacher_name': schedule.teacher.user.name,
            'room_name': schedule.room_name,
            'available_spots': schedule.max_students - current_enrollments,
            'max_students': schedule.max_students,
            'is_full': current_enrollments >= schedule.max_students
        })
    
    html = f"""
    <div class="row">
        <div class="col-md-8">
            <div class="d-flex align-items-center mb-3">
                <i class="{program.category.icon} display-4 me-3" style="color: {program.category.color}"></i>
                <div>
                    <h4>{program.name}</h4>
                    <p class="text-muted mb-0">{program.category.get_full_path()}</p>
                </div>
            </div>
            
            {f'<p class="mb-3">{program.short_description}</p>' if program.short_description else ''}
            {f'<div class="mb-3">{program.description}</div>' if program.description else ''}
            
            <div class="row g-3 mb-3">
                <div class="col-6">
                    <small class="text-muted">
                        <i class="bi bi-people me-1"></i>Age Range: {program.get_age_range()}
                    </small>
                </div>
                <div class="col-6">
                    <small class="text-muted">
                        <i class="bi bi-currency-dollar me-1"></i>Price: {program.get_price_display()}
                    </small>
                </div>
                {f'<div class="col-6"><small class="text-muted"><i class="bi bi-clock me-1"></i>Duration: {program.duration_minutes} minutes</small></div>' if program.duration_minutes else ''}
                <div class="col-6">
                    <small class="text-muted">
                        <i class="bi bi-person-check me-1"></i>Max Students: {program.max_students}
                    </small>
                </div>
            </div>
            
            {f'<div class="alert alert-info"><strong>Requirements:</strong> {program.requirements}</div>' if program.requirements else ''}
            {f'<div class="alert alert-success"><strong>Benefits:</strong> {program.benefits}</div>' if program.benefits else ''}
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0">Available Times</h6>
                </div>
                <div class="card-body">
    """
    
    if schedule_data:
        for schedule in schedule_data:
            status_color = 'success' if not schedule['is_full'] else 'danger'
            status_text = f"{schedule['available_spots']} spots left" if not schedule['is_full'] else 'Full'
            
            html += f"""
                    <div class="mb-3 p-2 border rounded">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong>{schedule['day_name']}</strong><br>
                                <small>{schedule['time_range']}</small><br>
                                <small class="text-muted">{schedule['teacher_name']}</small>
                                {f"<br><small class='text-muted'>{schedule['room_name']}</small>" if schedule['room_name'] else ''}
                            </div>
                            <span class="badge bg-{status_color}">{status_text}</span>
                        </div>
                    </div>
            """
    else:
        html += "<p class='text-muted'>No scheduled classes available.</p>"
    
    html += f"""
                </div>
            </div>
            
            <div class="mt-3 d-grid gap-2">
                <a href="/program/{program.id}" class="btn btn-primary">
                    <i class="bi bi-eye me-2"></i>View Full Details
                </a>
                <a href="/center/{program.center.id}" class="btn btn-outline-primary">
                    <i class="bi bi-building me-2"></i>View Center
                </a>
            </div>
        </div>
    </div>
    """
    
    return jsonify({
        'success': True,
        'html': html,
        'program': {
            'id': program.id,
            'name': program.name,
            'center_name': program.center.center_name
        }
    })

@app.route('/teacher/class/export')
@login_required(role='teacher')
def export_class_list():
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    class_name = request.args.get('class', '')
    
    schedules = Schedule.query.filter_by(teacher_id=teacher.id, is_active=True).all()
    target_schedule = None
    
    for schedule in schedules:
        schedule_name = f"{schedule.program.name} - {schedule.get_day_name()} {schedule.get_time_range()}"
        if schedule_name == class_name:
            target_schedule = schedule
            break
    
    if not target_schedule:
        flash('Class not found.', 'danger')
        return redirect(url_for('teacher_students'))
    
    enrollments = Enrollment.query.filter_by(
        schedule_id=target_schedule.id,
        status='active'
    ).all()
    
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Student Name', 'Age', 'Grade', 'Parent Name', 'Parent Email', 
        'Parent Phone', 'Enrollment Date', 'Notes'
    ])
    
    for enrollment in enrollments:
        child = enrollment.child
        parent = child.parent
        
        writer.writerow([
            child.name,
            child.calculate_age() or 'N/A',
            child.grade or 'N/A',
            parent.user.name,
            parent.user.email,
            parent.user.phone or 'N/A',
            enrollment.enrollment_date.strftime('%Y-%m-%d'),
            child.notes or 'N/A'
        ])
    
    output.seek(0)
    
    from flask import make_response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{class_name.replace(" ", "_")}_students.csv"'
    
    return response

@app.route('/enrollment/<int:enrollment_id>/cancel', methods=['POST'])
@login_required()
def cancel_enrollment(enrollment_id):
    user_role = session.get('user_role')
    
    if user_role == 'parent':
        parent = Parent.query.filter_by(user_id=session['user_id']).first()
        enrollment = Enrollment.query.join(Child).filter(
            Enrollment.id == enrollment_id,
            Child.parent_id == parent.id
        ).first()
    elif user_role == 'center':
        center = Center.query.filter_by(user_id=session['user_id']).first()
        enrollment = Enrollment.query.join(Schedule).join(Program).filter(
            Enrollment.id == enrollment_id,
            Program.center_id == center.id
        ).first()
    else:
        return jsonify({'error': 'Access denied'}), 403
    
    if not enrollment:
        return jsonify({'error': 'Enrollment not found'}), 404
    
    try:
        enrollment.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Enrollment cancelled for {enrollment.child.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel enrollment'}), 500

@app.route('/api/centers/search')
def api_centers_search():
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id')
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)
    max_price = request.args.get('max_price', type=float)
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    max_distance = request.args.get('max_distance', type=float, default=10.0)  # km
    
    centers_query = Center.query.filter(Center.latitude.isnot(None), Center.longitude.isnot(None))
    
    if query:
        centers_query = centers_query.filter(
            Center.center_name.contains(query) |
            Center.description.contains(query) |
            Center.address.contains(query)
        )
    
    centers = centers_query.all()
    
    if category_id:
        centers = [c for c in centers if any(
            p.category_id == int(category_id) and p.is_active 
            for p in c.programs
        )]
    
    if min_age is not None or max_age is not None:
        filtered_centers = []
        for center in centers:
            has_suitable_program = False
            for program in center.programs:
                if not program.is_active:
                    continue
                
                program_min = program.min_age or 0
                program_max = program.max_age or 100
                
                if min_age is not None and max_age is not None:
                    if not (program_max < min_age or program_min > max_age):
                        has_suitable_program = True
                        break
                elif min_age is not None:
                    if program_max >= min_age:
                        has_suitable_program = True
                        break
                elif max_age is not None:
                    if program_min <= max_age:
                        has_suitable_program = True
                        break
            
            if has_suitable_program:
                filtered_centers.append(center)
        
        centers = filtered_centers
    
    if max_price is not None:
        filtered_centers = []
        for center in centers:
            has_affordable_program = False
            for program in center.programs:
                if not program.is_active:
                    continue
                
                if (program.price_per_month and program.price_per_month <= max_price) or \
                   (program.price_per_session and program.price_per_session * 4 <= max_price):
                    has_affordable_program = True
                    break
            
            if has_affordable_program:
                filtered_centers.append(center)
        
        centers = filtered_centers
    
    if lat is not None and lng is not None:
        geocoding_service = GeocodingService()
        centers_with_distance = []
        
        for center in centers:
            distance = geocoding_service.get_distance(lat, lng, center.latitude, center.longitude)
            if distance <= max_distance:
                centers_with_distance.append({
                    'center': center,
                    'distance': distance
                })
        
        centers_with_distance.sort(key=lambda x: x['distance'])
        centers = [item['center'] for item in centers_with_distance]
    
    centers_data = []
    for center in centers:
        programs = [p for p in center.programs if p.is_active]
        
        center_data = {
            'id': center.id,
            'name': center.center_name,
            'description': center.description,
            'address': center.address,
            'latitude': center.latitude,
            'longitude': center.longitude,
            'phone': center.user.phone,
            'email': center.user.email,
            'programs_count': len(programs),
            'teachers_count': len(center.teachers),
            'programs': [
                {
                    'id': program.id,
                    'name': program.name,
                    'category': program.category.name,
                    'category_color': program.category.color,
                    'category_icon': program.category.icon,
                    'price': program.get_price_display(),
                    'age_range': program.get_age_range(),
                    'available_schedules': len([s for s in program.schedules if s.is_active])
                }
                for program in programs[:5]  
            ]
        }
        centers_data.append(center_data)
    
    return jsonify({
        'centers': centers_data,
        'total': len(centers_data),
        'filters_applied': {
            'query': query,
            'category_id': category_id,
            'min_age': min_age,
            'max_age': max_age,
            'max_price': max_price,
            'location_filter': lat is not None and lng is not None,
            'max_distance': max_distance
        }
    })

@app.route('/api/system/health')
def system_health():
    try:
        db.session.execute('SELECT 1')
        
        total_users = User.query.count()
        total_centers = Center.query.count()
        total_programs = Program.query.count()
        total_enrollments = Enrollment.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'stats': {
                'users': total_users,
                'centers': total_centers,
                'programs': total_programs,
                'enrollments': total_enrollments
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
    
@app.route('/api/enroll', methods=['POST'])
@login_required(role='parent')
def api_enroll_child_fixed():
    data = request.get_json()
    child_id = data.get('child_id')
    schedule_id = data.get('schedule_id')
    
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    schedule = Schedule.query.get(schedule_id)
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    existing = Enrollment.query.filter_by(
        child_id=child_id,
        schedule_id=schedule_id
    ).filter(Enrollment.status.in_(['active', 'pending'])).first()
    
    if existing:
        return jsonify({'error': 'Child is already enrolled or has a pending enrollment in this class'}), 400
    
    if child.birth_date:
        from datetime import date
        child_age = date.today().year - child.birth_date.year
        if schedule.program.min_age and child_age < schedule.program.min_age:
            return jsonify({'error': f'Child is too young for this program (minimum age: {schedule.program.min_age})'}), 400
        if schedule.program.max_age and child_age > schedule.program.max_age:
            return jsonify({'error': f'Child is too old for this program (maximum age: {schedule.program.max_age})'}), 400
    
    current_enrollments = Enrollment.query.filter_by(
        schedule_id=schedule_id
    ).filter(Enrollment.status.in_(['active', 'pending'])).count()
    
    if current_enrollments >= schedule.max_students:
        return jsonify({'error': 'Class is full'}), 400
    
    try:
        enrollment = Enrollment(
            child_id=child_id,
            schedule_id=schedule_id,
            status='pending', 
            created_by=session['user_id'],
            monthly_fee=schedule.program.price_per_month,
            session_fee=schedule.program.price_per_session
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{child.name} has been enrolled in {schedule.program.name}! Your enrollment is pending center approval.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Enrollment failed. Please try again.'}), 500

@app.route('/api/child/<int:child_id>/available-programs')
@login_required(role='parent')
def get_available_programs_for_child_fixed(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    child_age = None
    if child.birth_date:
        from datetime import date
        child_age = date.today().year - child.birth_date.year
    
    schedules = Schedule.query.filter_by(is_active=True).all()
    
    available_programs = []
    processed_programs = set()
    
    for schedule in schedules:
        if schedule.program.id in processed_programs:
            continue
        
        existing = Enrollment.query.filter_by(
            child_id=child_id,
            schedule_id=schedule.id
        ).filter(Enrollment.status.in_(['active', 'pending'])).first()
        
        if existing:
            continue
        
        if child_age:
            if schedule.program.min_age and child_age < schedule.program.min_age:
                continue
            if schedule.program.max_age and child_age > schedule.program.max_age:
                continue
        
        current_enrollments = Enrollment.query.filter_by(
            schedule_id=schedule.id
        ).filter(Enrollment.status.in_(['active', 'pending'])).count()
        
        if current_enrollments >= schedule.max_students:
            continue
        
        program_schedules = Schedule.query.filter_by(
            program_id=schedule.program.id,
            is_active=True
        ).all()
        
        available_schedules = []
        for prog_schedule in program_schedules:
            current_count = Enrollment.query.filter_by(
                schedule_id=prog_schedule.id
            ).filter(Enrollment.status.in_(['active', 'pending'])).count()
            
            if current_count < prog_schedule.max_students:
                available_schedules.append({
                    'id': prog_schedule.id,
                    'day_name': prog_schedule.get_day_name(),
                    'time_range': prog_schedule.get_time_range(),
                    'teacher_name': prog_schedule.teacher.user.name,
                    'room_name': prog_schedule.room_name,
                    'available_spots': prog_schedule.max_students - current_count,
                    'max_students': prog_schedule.max_students
                })
        
        if available_schedules:
            program_data = {
                'id': schedule.program.id,
                'name': schedule.program.name,
                'short_description': schedule.program.short_description,
                'description': schedule.program.description,
                'center_name': schedule.program.center.center_name,
                'center_id': schedule.program.center.id,
                'category_icon': schedule.program.category.icon,
                'category_color': schedule.program.category.color,
                'category_name': schedule.program.category.name,
                'price_display': schedule.program.get_price_display(),
                'age_range': schedule.program.get_age_range(),
                'duration_minutes': schedule.program.duration_minutes,
                'schedules': available_schedules
            }
            
            available_programs.append(program_data)
            processed_programs.add(schedule.program.id)
    
    return jsonify({'programs': available_programs})

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.route('/enroll-from-program/<int:program_id>')
@login_required(role='parent')
def enroll_from_program(program_id):
    program = Program.query.get_or_404(program_id)
    
    schedule = Schedule.query.filter_by(program_id=program_id, is_active=True).first()
    
    if schedule:
        return redirect(url_for('parent_dashboard', enroll_schedule=schedule.id))
    else:
        flash('No available class schedules for this program.', 'warning')
        return redirect(url_for('view_program', program_id=program_id))

def create_tables():
    """Create database tables"""
    with app.app_context():
        db.create_all()
        init_default_categories()

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host='localhost', port=5000)