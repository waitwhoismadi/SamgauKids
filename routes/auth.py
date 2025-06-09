from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User, Parent, Center, Teacher
from services import GeocodingService
from utils import save_uploaded_file, get_user_dashboard_url

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
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
            return redirect(get_user_dashboard_url())
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register')
def register_choice():
    return render_template('auth/register_choice.html')

@auth_bp.route('/register/parent', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register_parent.html')
    
    return render_template('auth/register_parent.html')

@auth_bp.route('/register/center', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register_center.html')
    
    return render_template('auth/register_center.html')

@auth_bp.route('/register/teacher', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register_teacher.html')
    
    return render_template('auth/register_teacher.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('public.index'))