from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import time, datetime
from database import db
from models import Center, Teacher, Program, Schedule, Category, Enrollment, User
from services import GeocodingService
from email_service import email_service  
from utils import login_required, save_uploaded_file

center_bp = Blueprint('center', __name__)

@center_bp.route('/dashboard')
@login_required(role='center')
def dashboard():
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

@center_bp.route('/programs')
@login_required(role='center')
def programs():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    programs = Program.query.filter_by(center_id=center.id).all() if center else []
    categories = Category.query.all()
    
    return render_template('center/programs.html', 
                         center=center, 
                         programs=programs,
                         categories=categories)

@center_bp.route('/programs/add', methods=['GET', 'POST'])
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
            return redirect(url_for('center.programs'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the program. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('center/add_program.html', center=center, categories=categories)

@center_bp.route('/programs/<int:program_id>/edit', methods=['GET', 'POST'])
@login_required(role='center')
def edit_program(program_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    program = Program.query.filter_by(id=program_id, center_id=center.id).first()
    
    if not program:
        flash('Program not found.', 'danger')
        return redirect(url_for('center.programs'))
    
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
            return redirect(url_for('center.programs'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the program. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('center/edit_program.html', center=center, program=program, categories=categories)

@center_bp.route('/programs/<int:program_id>/delete', methods=['POST'])
@login_required(role='center')
def delete_program(program_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    program = Program.query.filter_by(id=program_id, center_id=center.id).first()
    
    if not program:
        flash('Program not found.', 'danger')
        return redirect(url_for('center.programs'))
    
    try:
        active_enrollments = db.session.query(Enrollment).join(Schedule).filter(
            Schedule.program_id == program.id,
            Enrollment.status == 'active'
        ).count()
        
        if active_enrollments > 0:
            flash(f'Cannot delete program with {active_enrollments} active enrollments.', 'danger')
            return redirect(url_for('center.programs'))
        
        program_name = program.name
        db.session.delete(program)
        db.session.commit()
        flash(f'Program "{program_name}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the program. Please try again.', 'danger')
    
    return redirect(url_for('center.programs'))

@center_bp.route('/schedules')
@login_required(role='center')
def schedules():
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

@center_bp.route('/schedules/add', methods=['GET', 'POST'])
@login_required(role='center')
def add_schedule():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    if request.method == 'POST':
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
            return redirect(url_for('center.schedules'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the schedule. Please try again.', 'danger')
    
    programs = Program.query.filter_by(center_id=center.id, is_active=True).all() if center else []
    teachers = Teacher.query.filter_by(center_id=center.id).all() if center else []
    
    return render_template('center/add_schedule.html', 
                         center=center, 
                         programs=programs,
                         teachers=teachers)

@center_bp.route('/enrollments')
@login_required(role='center')
def enrollments():
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

@center_bp.route('/enrollment/<int:enrollment_id>/approve', methods=['POST'])
@login_required(role='center')
def approve_enrollment(enrollment_id):
    try:
        center = Center.query.filter_by(user_id=session['user_id']).first()
        if not center:
            return jsonify({'error': 'Center profile not found'}), 404
            
        enrollment = db.session.query(Enrollment).join(Schedule).join(Program).filter(
            Enrollment.id == enrollment_id,
            Program.center_id == center.id,
            Enrollment.status == 'pending'
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'Enrollment not found or already processed'}), 404
        
        current_count = Enrollment.query.filter_by(
            schedule_id=enrollment.schedule_id
        ).filter(Enrollment.status.in_(['active', 'pending'])).count()
        
        if current_count > enrollment.schedule.max_students:
            return jsonify({'error': 'Class is now full, cannot approve'}), 400
        
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

@center_bp.route('/profile', methods=['GET', 'POST'])
@login_required(role='center')
def profile():
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
            return redirect(url_for('center.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')
    
    return render_template('center/profile.html', center=center)

@center_bp.route('/regenerate-invite-code', methods=['POST'])
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

@center_bp.route('/teachers')
@login_required(role='center')
def teachers():
    center = Center.query.filter_by(user_id=session['user_id']).first()
    teachers = Teacher.query.filter_by(center_id=center.id).all() if center else []
    
    return render_template('center/teachers.html', center=center, teachers=teachers)

@center_bp.route('/teacher/<int:teacher_id>/remove', methods=['POST'])
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
    
@center_bp.route('/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required(role='center')
def edit_schedule(schedule_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    schedule = Schedule.query.join(Program).filter(
        Schedule.id == schedule_id,
        Program.center_id == center.id
    ).first()
    
    if not schedule:
        flash('Schedule not found.', 'danger')
        return redirect(url_for('center.schedules'))
    
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
            return redirect(url_for('center.schedules'))
            
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

@center_bp.route('/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required(role='center')
def delete_schedule(schedule_id):
    center = Center.query.filter_by(user_id=session['user_id']).first()
    
    schedule = Schedule.query.join(Program).filter(
        Schedule.id == schedule_id,
        Program.center_id == center.id
    ).first()
    
    if not schedule:
        flash('Schedule not found.', 'danger')
        return redirect(url_for('center.schedules'))
    
    try:
        active_enrollments = Enrollment.query.filter(
            Enrollment.schedule_id == schedule_id,
            Enrollment.status == 'active'
        ).count()
        
        if active_enrollments > 0:
            flash(f'Cannot delete schedule with {active_enrollments} active enrollments. Please cancel enrollments first.', 'danger')
            return redirect(url_for('center.schedules'))
        
        schedule_info = f"{schedule.program.name} - {schedule.get_day_name()} {schedule.get_time_range()}"
        db.session.delete(schedule)
        db.session.commit()
        
        flash(f'Schedule "{schedule_info}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the schedule. Please try again.', 'danger')
    
    return redirect(url_for('center.schedules'))
