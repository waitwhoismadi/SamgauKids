from functools import wraps
from flask import session, flash, redirect, url_for, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from database import db
from models import Category

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if role and session.get('user_role') != role:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('public.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def save_uploaded_file(file, folder='general'):
    if file and file.filename:
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        return f"{folder}/{filename}"
    return None

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

def get_user_dashboard_url():
    role = session.get('user_role')
    if role == 'parent':
        return url_for('parent.dashboard')
    elif role == 'center':
        return url_for('center.dashboard')
    elif role == 'teacher':
        return url_for('teacher.dashboard')
    else:
        return url_for('public.index')