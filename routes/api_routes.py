from flask import Blueprint, jsonify, request, session
from datetime import datetime, date
from database import db
from models import (Center, Program, Category, Schedule, Enrollment, Child, Parent, 
                   Teacher, User)
from services import GeocodingService
from utils import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/centers')
def centers():
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

@api_bp.route('/centers/search')
def centers_search():
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

@api_bp.route('/child/<int:child_id>/available-programs')
@login_required(role='parent')
def get_available_programs_for_child(child_id):
    try:
        parent = Parent.query.filter_by(user_id=session['user_id']).first()
        if not parent:
            return jsonify({'error': 'Parent profile not found'}), 404
            
        child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
        if not child:
            return jsonify({'error': 'Child not found'}), 404
        
        child_age = None
        if child.birth_date:
            child_age = date.today().year - child.birth_date.year
        
        schedules = Schedule.query.filter_by(is_active=True).all()
        
        available_programs = []
        processed_programs = set()
        
        for schedule in schedules:
            if schedule.program.id in processed_programs:
                continue
            
            # FIXED: Check if child is already enrolled in this program
            existing_in_program = Enrollment.query.join(Schedule).filter(
                Schedule.program_id == schedule.program.id,
                Enrollment.child_id == child_id,
                Enrollment.status.in_(['active', 'pending'])
            ).first()
            
            if existing_in_program:
                continue
            
            # Check age requirements
            if child_age:
                if schedule.program.min_age and child_age < schedule.program.min_age:
                    continue
                if schedule.program.max_age and child_age > schedule.program.max_age:
                    continue
            
            # Get all schedules for this program
            program_schedules = Schedule.query.filter_by(
                program_id=schedule.program.id,
                is_active=True
            ).all()
            
            available_schedules = []
            for prog_schedule in program_schedules:
                # FIXED: Check if child is already enrolled in this specific schedule
                existing_in_schedule = Enrollment.query.filter(
                    Enrollment.child_id == child_id,
                    Enrollment.schedule_id == prog_schedule.id,
                    Enrollment.status.in_(['active', 'pending'])
                ).first()
                
                if existing_in_schedule:
                    continue
                
                # FIXED: Check capacity
                current_count = Enrollment.query.filter(
                    Enrollment.schedule_id == prog_schedule.id,
                    Enrollment.status.in_(['active', 'pending'])
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
        
    except Exception as e:
        return jsonify({'error': 'Failed to load programs'}), 500

@api_bp.route('/child/<int:child_id>/enrollments')
@login_required(role='parent')
def child_enrollments(child_id):
    try:
        parent = Parent.query.filter_by(user_id=session['user_id']).first()
        if not parent:
            return jsonify({'error': 'Parent profile not found'}), 404
            
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
        
    except Exception as e:
        return jsonify({'error': 'Failed to load enrollments'}), 500

@api_bp.route('/enroll', methods=['POST'])
@login_required(role='parent')
def enroll_child():
    try:
        data = request.get_json()
        child_id = data.get('child_id')
        schedule_id = data.get('schedule_id')
        
        if not child_id or not schedule_id:
            return jsonify({'error': 'Missing child_id or schedule_id'}), 400
        
        parent = Parent.query.filter_by(user_id=session['user_id']).first()
        if not parent:
            return jsonify({'error': 'Parent profile not found'}), 404
            
        child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
        if not child:
            return jsonify({'error': 'Child not found or access denied'}), 404
        
        schedule = Schedule.query.filter_by(id=schedule_id, is_active=True).first()
        if not schedule:
            return jsonify({'error': 'Schedule not found or inactive'}), 404
        
        existing = Enrollment.query.filter(
            Enrollment.child_id == child_id,
            Enrollment.schedule_id == schedule_id,
            Enrollment.status.in_(['active', 'pending'])
        ).first()
        
        if existing:
            return jsonify({'error': 'Child is already enrolled or has a pending enrollment in this class'}), 400
        
        if child.birth_date:
            child_age = date.today().year - child.birth_date.year
            if schedule.program.min_age and child_age < schedule.program.min_age:
                return jsonify({'error': f'Child is too young for this program (minimum age: {schedule.program.min_age})'}), 400
            if schedule.program.max_age and child_age > schedule.program.max_age:
                return jsonify({'error': f'Child is too old for this program (maximum age: {schedule.program.max_age})'}), 400
        
        current_enrollments = Enrollment.query.filter(
            Enrollment.schedule_id == schedule_id,
            Enrollment.status.in_(['active', 'pending'])
        ).count()
        
        if current_enrollments >= schedule.max_students:
            return jsonify({'error': 'Class is full'}), 400
        
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
        
        try:
            email_service.send_enrollment_confirmation(enrollment)
            
            email_service.send_enrollment_notification_to_center(enrollment)
        except Exception as e:
            current_app.logger.error(f'Failed to send enrollment emails: {str(e)}')
        
        return jsonify({
            'success': True,
            'message': f'{child.name} has been enrolled in {schedule.program.name}! Your enrollment is pending center approval. Check your email for confirmation details.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Enrollment failed. Please try again.'}), 500

@api_bp.route('/program/<int:program_id>/details')
def program_details(program_id):
    program = Program.query.get_or_404(program_id)
    
    if not program.is_active:
        return jsonify({'success': False, 'error': 'Program not available'}), 404
    
    schedules = Schedule.query.filter_by(program_id=program.id, is_active=True).all()
    
    schedule_data = []
    for schedule in schedules:
        current_enrollments = Enrollment.query.filter(
            Enrollment.schedule_id == schedule.id,
            Enrollment.status.in_(['active', 'pending'])
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

@api_bp.route('/center/<int:center_id>/stats')
def center_stats(center_id):
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

@api_bp.route('/geocode')
def geocode():
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

@api_bp.route('/distance')
def distance():
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

@api_bp.route('/system/health')
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

@api_bp.route('/enrollment/<int:enrollment_id>/cancel', methods=['POST'])
@login_required()
def cancel_enrollment(enrollment_id):
    try:
        user_role = session.get('user_role')
        
        if user_role == 'parent':
            parent = Parent.query.filter_by(user_id=session['user_id']).first()
            if not parent:
                return jsonify({'error': 'Parent profile not found'}), 404
                
            enrollment = Enrollment.query.join(Child).filter(
                Enrollment.id == enrollment_id,
                Child.parent_id == parent.id
            ).first()
        elif user_role == 'center':
            center = Center.query.filter_by(user_id=session['user_id']).first()
            if not center:
                return jsonify({'error': 'Center profile not found'}), 404
                
            enrollment = Enrollment.query.join(Schedule).join(Program).filter(
                Enrollment.id == enrollment_id,
                Program.center_id == center.id
            ).first()
        else:
            return jsonify({'error': 'Access denied'}), 403
        
        if not enrollment:
            return jsonify({'error': 'Enrollment not found or access denied'}), 404
        
        enrollment.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Enrollment cancelled for {enrollment.child.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel enrollment'}), 500