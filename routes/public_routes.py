from flask import Blueprint, render_template, redirect, url_for, session, flash
from models import Center, Program, Schedule, Enrollment, Teacher
from utils import login_required

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('public.dashboard'))
    return render_template('index.html')

@public_bp.route('/dashboard')
@login_required()
def dashboard():
    role = session.get('user_role')
    
    if role == 'parent':
        return redirect(url_for('parent.dashboard'))
    elif role == 'center':
        return redirect(url_for('center.dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher.dashboard'))
    else:
        flash('Invalid user role', 'danger')
        return redirect(url_for('auth.logout'))

@public_bp.route('/program/<int:program_id>')
def view_program(program_id):
    program = Program.query.get_or_404(program_id)
    if not program.is_active:
        flash('This program is currently not available.', 'warning')
        return redirect(url_for('public.index'))
    
    schedules = Schedule.query.filter_by(program_id=program.id, is_active=True).all()
    
    schedule_availability = []
    for schedule in schedules:
        current_enrollments = Enrollment.query.filter(
            Enrollment.schedule_id == schedule.id,
            Enrollment.status.in_(['active', 'pending'])
        ).count()
        
        schedule_availability.append({
            'schedule': schedule,
            'available_spots': schedule.max_students - current_enrollments,
            'is_full': current_enrollments >= schedule.max_students
        })
    
    return render_template('public/program_detail.html', 
                         program=program, 
                         schedule_availability=schedule_availability)

@public_bp.route('/center/<int:center_id>')
def view_center(center_id):
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

@public_bp.route('/enroll-from-program/<int:program_id>')
@login_required(role='parent')
def enroll_from_program(program_id):
    program = Program.query.get_or_404(program_id)
    
    schedule = Schedule.query.filter_by(program_id=program_id, is_active=True).first()
    
    if schedule:
        return redirect(url_for('parent.dashboard', enroll_schedule=schedule.id))
    else:
        flash('No available class schedules for this program.', 'warning')
        return redirect(url_for('public.view_program', program_id=program_id))