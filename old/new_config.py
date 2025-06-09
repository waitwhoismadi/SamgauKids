# config.py - Create this file for better configuration management
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///education_platform.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
    
    # App settings
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:5000'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Add production-specific settings here

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Add these enhancements to your main app.py file:

# Enhanced imports at the top of app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid
from datetime import datetime, date, timedelta
import logging
from logging.handlers import RotatingFileHandler

# Import the config
from config import config
from email_service import EmailService

# Enhanced Flask app initialization
def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_CONFIG') or 'default'
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    from database import db
    db.init_app(app)
    
    # Initialize email service
    email_service = EmailService()
    email_service.init_app(app)
    
    # Register blueprints (if you want to organize routes)
    # from routes import auth_bp, main_bp, api_bp
    # app.register_blueprint(auth_bp, url_prefix='/auth')
    # app.register_blueprint(main_bp)
    # app.register_blueprint(api_bp, url_prefix='/api')
    
    # Set up logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/kidfit.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('KidFit startup')
    
    return app

# Enhanced enrollment route with email notifications
@app.route('/api/enroll', methods=['POST'])
@login_required(role='parent')
def api_enroll_child_with_email():
    """Enhanced enrollment API with email notifications"""
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
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        child_id=child_id,
        schedule_id=schedule_id
    ).filter(Enrollment.status.in_(['active', 'pending'])).first()
    
    if existing:
        return jsonify({'error': 'Child is already enrolled or has a pending enrollment in this class'}), 400
    
    # Check age requirements
    if child.birth_date:
        child_age = date.today().year - child.birth_date.year
        if schedule.program.min_age and child_age < schedule.program.min_age:
            return jsonify({'error': f'Child is too young for this program (minimum age: {schedule.program.min_age})'}), 400
        if schedule.program.max_age and child_age > schedule.program.max_age:
            return jsonify({'error': f'Child is too old for this program (maximum age: {schedule.program.max_age})'}), 400
    
    # Check capacity
    current_enrollments = Enrollment.query.filter_by(
        schedule_id=schedule_id
    ).filter(Enrollment.status.in_(['active', 'pending'])).count()
    
    if current_enrollments >= schedule.max_students:
        return jsonify({'error': 'Class is full'}), 400
    
    # Create enrollment
    try:
        enrollment = Enrollment(
            child_id=child_id,
            schedule_id=schedule_id,
            status='pending',  # Require center approval
            created_by=session['user_id'],
            monthly_fee=schedule.program.price_per_month,
            session_fee=schedule.program.price_per_session
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        # Send email notification
        try:
            email_service.send_enrollment_confirmation(enrollment)
        except Exception as e:
            app.logger.error(f"Failed to send enrollment email: {str(e)}")
            # Don't fail the enrollment if email fails
        
        return jsonify({
            'success': True,
            'message': f'{child.name} has been enrolled in {schedule.program.name}! Your enrollment is pending center approval. You\'ll receive an email confirmation shortly.'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Enrollment failed: {str(e)}")
        return jsonify({'error': 'Enrollment failed. Please try again.'}), 500

# Enhanced center approval with email notifications
@app.route('/center/enrollment/<int:enrollment_id>/approve', methods=['POST'])
@login_required(role='center')
def approve_enrollment_with_email(enrollment_id):
    """Approve enrollment with email notification"""
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
        
        # Send email notification
        try:
            email_service.send_enrollment_status_update(enrollment, 'active')
        except Exception as e:
            app.logger.error(f"Failed to send approval email: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'Enrollment approved for {enrollment.child.name}. Parent has been notified by email.'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to approve enrollment: {str(e)}")
        return jsonify({'error': 'Failed to approve enrollment'}), 500

# Enhanced teacher invitation with email
@app.route('/center/invite-teacher', methods=['POST'])
@login_required(role='center')
def invite_teacher_by_email():
    """Invite teacher via email"""
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    data = request.get_json()
    teacher_email = data.get('email')
    
    if not teacher_email:
        return jsonify({'error': 'Email address is required'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=teacher_email).first()
    if existing_user:
        return jsonify({'error': 'A user with this email already exists'}), 400
    
    try:
        # Send invitation email
        email_service.send_teacher_invitation(center, teacher_email, center.invite_code)
        
        return jsonify({
            'success': True,
            'message': f'Invitation sent to {teacher_email}'
        })
    except Exception as e:
        app.logger.error(f"Failed to send teacher invitation: {str(e)}")
        return jsonify({'error': 'Failed to send invitation email'}), 500

# Enhanced demo data creation
@app.route('/admin/create-demo-data')
def create_enhanced_demo_data():
    """Create comprehensive demo data"""
    if not app.debug:
        return "This function is only available in debug mode", 403
    
    try:
        # Create demo categories if they don't exist
        if Category.query.count() == 0:
            init_default_categories()
        
        # Create multiple demo centers
        demo_centers_data = [
            {
                'name': 'Astana Kids Academy',
                'email': 'demo@center1.com',
                'description': 'Premium education center offering diverse programs for children and teenagers.',
                'address': 'Nur-Sultan, Yessil District, Mangilik El Avenue 53',
                'lat': 51.1282,
                'lng': 71.4306
            },
            {
                'name': 'Future Stars Education',
                'email': 'demo@center2.com',
                'description': 'Specialized in STEM education and creative arts programs.',
                'address': 'Nur-Sultan, Saryarka District, Kabanbay Batyr Avenue 15',
                'lat': 51.1605,
                'lng': 71.4704
            },
            {
                'name': 'Little Genius Center',
                'email': 'demo@center3.com',
                'description': 'Early childhood development and language learning programs.',
                'address': 'Nur-Sultan, Almaty District, Turan Avenue 42',
                'lat': 51.1150,
                'lng': 71.4200
            }
        ]
        
        for center_data in demo_centers_data:
            existing_user = User.query.filter_by(email=center_data['email']).first()
            if not existing_user:
                # Create center user
                center_user = User(
                    email=center_data['email'],
                    password_hash=generate_password_hash('demo123'),
                    name=f"{center_data['name']} Admin",
                    phone='+7 701 234 5678',
                    role='center'
                )
                db.session.add(center_user)
                db.session.flush()
                
                # Create center
                center = Center(
                    user_id=center_user.id,
                    center_name=center_data['name'],
                    description=center_data['description'],
                    address=center_data['address'],
                    latitude=center_data['lat'],
                    longitude=center_data['lng']
                )
                db.session.add(center)
                db.session.flush()
                
                # Create demo programs for each center
                sports_category = Category.query.filter_by(name='Sports').first()
                arts_category = Category.query.filter_by(name='Arts & Crafts').first()
                tech_category = Category.query.filter_by(name='Technology').first()
                
                demo_programs = [
                    {
                        'name': 'Kids Football',
                        'category': sports_category,
                        'description': 'Learn football basics in a fun, safe environment.',
                        'price_per_month': 15000,
                        'min_age': 6,
                        'max_age': 14
                    },
                    {
                        'name': 'Creative Arts',
                        'category': arts_category,
                        'description': 'Explore creativity through painting, drawing, and crafts.',
                        'price_per_month': 12000,
                        'min_age': 4,
                        'max_age': 12
                    },
                    {
                        'name': 'Junior Robotics',
                        'category': tech_category,
                        'description': 'Introduction to robotics and programming for kids.',
                        'price_per_month': 20000,
                        'min_age': 8,
                        'max_age': 16
                    }
                ]
                
                for prog_data in demo_programs:
                    if prog_data['category']:
                        program = Program(
                            center_id=center.id,
                            category_id=prog_data['category'].id,
                            name=prog_data['name'],
                            description=prog_data['description'],
                            short_description=prog_data['description'][:100],
                            price_per_month=prog_data['price_per_month'],
                            duration_minutes=60,
                            min_age=prog_data['min_age'],
                            max_age=prog_data['max_age'],
                            max_students=15
                        )
                        db.session.add(program)
        
        # Create demo parent families
        demo_families = [
            {
                'parent_name': 'Sarah Johnson',
                'parent_email': 'parent1@demo.com',
                'children': [
                    {'name': 'Emma Johnson', 'age': 8, 'grade': '3rd Grade'},
                    {'name': 'Liam Johnson', 'age': 6, 'grade': '1st Grade'}
                ]
            },
            {
                'parent_name': 'Michael Chen',
                'parent_email': 'parent2@demo.com',
                'children': [
                    {'name': 'Sophie Chen', 'age': 10, 'grade': '5th Grade'}
                ]
            }
        ]
        
        for family_data in demo_families:
            existing_user = User.query.filter_by(email=family_data['parent_email']).first()
            if not existing_user:
                # Create parent user
                parent_user = User(
                    email=family_data['parent_email'],
                    password_hash=generate_password_hash('demo123'),
                    name=family_data['parent_name'],
                    phone='+7 701 987 6543',
                    role='parent'
                )
                db.session.add(parent_user)
                db.session.flush()
                
                # Create parent
                parent = Parent(
                    user_id=parent_user.id,
                    address='Nur-Sultan, Yessil District, Turan Avenue 37'
                )
                db.session.add(parent)
                db.session.flush()
                
                # Create children
                for child_data in family_data['children']:
                    birth_year = date.today().year - child_data['age']
                    child = Child(
                        parent_id=parent.id,
                        name=child_data['name'],
                        birth_date=date(birth_year, 1, 1),
                        grade=child_data['grade']
                    )
                    db.session.add(child)
        
        db.session.commit()
        
        return """
        <h2>Demo data created successfully!</h2>
        <h3>Test Accounts:</h3>
        <h4>Centers:</h4>
        <ul>
            <li>demo@center1.com / demo123 (Astana Kids Academy)</li>
            <li>demo@center2.com / demo123 (Future Stars Education)</li>
            <li>demo@center3.com / demo123 (Little Genius Center)</li>
        </ul>
        <h4>Parents:</h4>
        <ul>
            <li>parent1@demo.com / demo123 (Sarah Johnson - 2 children)</li>
            <li>parent2@demo.com / demo123 (Michael Chen - 1 child)</li>
        </ul>
        <p><a href="/">← Back to Home</a></p>
        """
        
    except Exception as e:
        db.session.rollback()
        return f"Error creating demo data: {str(e)}", 500

# Add system status endpoint
@app.route('/api/system/status')
def system_status():
    """System status endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        # Get basic stats
        stats = {
            'users': User.query.count(),
            'centers': Center.query.count(),
            'programs': Program.query.count(),
            'active_enrollments': Enrollment.query.filter_by(status='active').count(),
            'total_enrollments': Enrollment.query.count()
        }
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat(),
            'stats': stats,
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500