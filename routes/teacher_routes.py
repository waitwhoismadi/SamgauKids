from flask import Blueprint, render_template, session, request, jsonify, make_response
from datetime import date, datetime
from database import db
from models import Teacher, Schedule, Enrollment, Attendance, Parent
from utils import login_required
import io
import csv

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/dashboard')
@login_required(role='teacher')
def dashboard():
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

@teacher_bp.route('/schedule')
@login_required(role='teacher')
def schedule():
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

@teacher_bp.route('/students')
@login_required(role='teacher')
def students():
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

@teacher_bp.route('/student/<int:child_id>/details')
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

@teacher_bp.route('/parent/<int:parent_id>/contact')
@login_required(role='teacher')
def parent_contact_api(parent_id):
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    parent = Parent.query.get(parent_id)
    
    if not parent:
        return jsonify({'success': False}), 404
    
    # Verify teacher has access to this parent through their children
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

@teacher_bp.route('/attendance/mark', methods=['POST'])
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

@teacher_bp.route('/class/export')
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
        return jsonify({'error': 'Class not found'}), 404
    
    enrollments = Enrollment.query.filter_by(
        schedule_id=target_schedule.id,
        status='active'
    ).all()
    
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
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{class_name.replace(" ", "_")}_students.csv"'
    
    return response