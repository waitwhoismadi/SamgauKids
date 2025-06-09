from database import db
from datetime import datetime, time, date
import secrets

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False)  
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

class Parent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address = db.Column(db.String(200))
    
    user = db.relationship('User', backref=db.backref('parent_profile', uselist=False))
    
    def __repr__(self):
        return f'<Parent {self.user.name}>'

class Center(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    center_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float) 
    longitude = db.Column(db.Float) 
    photo_url = db.Column(db.String(255))
    website = db.Column(db.String(255))
    schedule_info = db.Column(db.Text)  
    invite_code = db.Column(db.String(8), unique=True)  
    
    user = db.relationship('User', backref=db.backref('center_profile', uselist=False))

    def __init__(self, **kwargs):
        super(Center, self).__init__(**kwargs)
        if not self.invite_code:
            self.invite_code = self.generate_invite_code()

    def generate_invite_code(self):
        while True:
            code = secrets.token_hex(4).upper()  
            existing = Center.query.filter_by(invite_code=code).first()
            if not existing:
                return code

    def __repr__(self):
        return f'<Center {self.center_name}>'

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    center_id = db.Column(db.Integer, db.ForeignKey('center.id'), nullable=False)
    specialization = db.Column(db.String(100))
    bio = db.Column(db.Text)
    hire_date = db.Column(db.Date, default=datetime.utcnow().date)
    
    user = db.relationship('User', backref=db.backref('teacher_profile', uselist=False))
    center = db.relationship('Center', backref=db.backref('teachers', lazy=True))

    def __repr__(self):
        return f'<Teacher {self.user.name} at {self.center.center_name}>'

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date)
    grade = db.Column(db.String(20))
    notes = db.Column(db.Text)
    photo_url = db.Column(db.String(255)) 
    medical_info = db.Column(db.Text)  
    emergency_contact = db.Column(db.String(100))  
    emergency_phone = db.Column(db.String(20))  
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    parent = db.relationship('Parent', backref=db.backref('children', lazy=True))
    
    def calculate_age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None
    
    def get_age_display(self):
        age = self.calculate_age()
        if age:
            return f"{age} years old"
        return "Age not specified"

    def __repr__(self):
        return f'<Child {self.name}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    icon = db.Column(db.String(50))  
    color = db.Column(db.String(7), default='#6c757d')  
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    parent = db.relationship('Category', remote_side=[id], backref='subcategories')
    
    def get_full_path(self):
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' → '.join(path)
    
    def get_all_children(self):
        children = list(self.subcategories)
        for child in self.subcategories:
            children.extend(child.get_all_children())
        return children

    def __repr__(self):
        return f'<Category {self.get_full_path()}>'

class Program(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    center_id = db.Column(db.Integer, db.ForeignKey('center.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(255))
    
    price_per_month = db.Column(db.Float)
    price_per_session = db.Column(db.Float)
    duration_minutes = db.Column(db.Integer) 
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    max_students = db.Column(db.Integer, default=20)
    
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    
    requirements = db.Column(db.Text)  
    benefits = db.Column(db.Text)    
    photo_url = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    center = db.relationship('Center', backref=db.backref('programs', lazy=True))
    category = db.relationship('Category', backref=db.backref('programs', lazy=True))
    
    def get_age_range(self):
        if self.min_age and self.max_age:
            return f"{self.min_age}-{self.max_age} years"
        elif self.min_age:
            return f"{self.min_age}+ years"
        elif self.max_age:
            return f"Up to {self.max_age} years"
        return "All ages"
    
    def get_price_display(self):
        prices = []
        if self.price_per_month:
            prices.append(f"{self.price_per_month:,.0f}₸/month")
        if self.price_per_session:
            prices.append(f"{self.price_per_session:,.0f}₸/session")
        return " or ".join(prices) if prices else "Contact for pricing"
    
    def get_available_spots(self):
        total_spots = 0
        taken_spots = 0
        
        for schedule in self.schedules:
            if schedule.is_active:
                total_spots += schedule.max_students
                taken_spots += len([e for e in schedule.enrollments if e.status == 'active'])
        
        return max(0, total_spots - taken_spots)

    def __repr__(self):
        return f'<Program {self.name} at {self.center.center_name}>'

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    
    day_of_week = db.Column(db.Integer, nullable=False)  
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    max_students = db.Column(db.Integer, default=20)
    room_name = db.Column(db.String(100)) 
    notes = db.Column(db.Text)  
    
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date, default=datetime.utcnow().date)  
    end_date = db.Column(db.Date)  

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    program = db.relationship('Program', backref=db.backref('schedules', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('schedules', lazy=True))
    
    def get_day_name(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.day_of_week]
    
    def get_time_range(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    def get_duration_minutes(self):
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return end_minutes - start_minutes
    
    def conflicts_with(self, other_schedule):
        if self.day_of_week != other_schedule.day_of_week:
            return False
        if self.teacher_id != other_schedule.teacher_id:
            return False
        
        return not (self.end_time <= other_schedule.start_time or 
                   self.start_time >= other_schedule.end_time)
    
    def get_enrollment_count(self):
        return len([e for e in self.enrollments if e.status == 'active'])
    
    def get_available_spots(self):
        return max(0, self.max_students - self.get_enrollment_count())
    
    def is_full(self):
        return self.get_enrollment_count() >= self.max_students
    
    def __repr__(self):
        return f'<Schedule {self.program.name} - {self.get_day_name()} {self.get_time_range()}>'
    
    def get_enrollment_count_by_status(self, status=None):
        if status:
            return len([e for e in self.enrollments if e.status == status])
        return len(self.enrollments)

    def get_active_enrollment_count(self):
        return self.get_enrollment_count_by_status('active')

    def get_pending_enrollment_count(self):
        return self.get_enrollment_count_by_status('pending')

    def get_total_enrollment_count(self):
        return len([e for e in self.enrollments if e.status in ['active', 'pending']])

    def get_available_spots(self):
        return max(0, self.max_students - self.get_total_enrollment_count())

    def is_full(self):
        return self.get_total_enrollment_count() >= self.max_students

    def has_availability(self):
        return self.get_available_spots() > 0

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    
    enrollment_date = db.Column(db.Date, default=date.today)
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)  
    status = db.Column(db.String(20), default='pending')  
    
    payment_method = db.Column(db.String(50))  
    monthly_fee = db.Column(db.Float)
    session_fee = db.Column(db.Float)
    total_paid = db.Column(db.Float, default=0.0)
    outstanding_balance = db.Column(db.Float, default=0.0)
    next_payment_due = db.Column(db.Date)
    
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))  
    approved_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    child = db.relationship('Child', backref=db.backref('enrollments', lazy=True))
    schedule = db.relationship('Schedule', backref=db.backref('enrollments', lazy=True))
    creator = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def get_program_name(self):
        return self.schedule.program.name
    
    def get_center_name(self):
        return self.schedule.program.center.center_name
    
    def get_schedule_info(self):
        return f"{self.schedule.get_day_name()} {self.schedule.get_time_range()}"
    
    def get_full_schedule_info(self):
        info = self.get_schedule_info()
        if self.schedule.room_name:
            info += f" in {self.schedule.room_name}"
        info += f" with {self.schedule.teacher.user.name}"
        return info
    
    def calculate_monthly_fee(self):
        if self.schedule.program.price_per_month:
            return self.schedule.program.price_per_month
        elif self.schedule.program.price_per_session:
            return self.schedule.program.price_per_session * 4
        return 0.0
    
    def is_payment_overdue(self):
        if self.next_payment_due and self.outstanding_balance > 0:
            return date.today() > self.next_payment_due
        return False
    
    def get_status_display(self):
        status_map = {
            'pending': 'Pending Approval',
            'active': 'Active',
            'paused': 'Paused',
            'cancelled': 'Cancelled',
            'completed': 'Completed'
        }
        return status_map.get(self.status, self.status.title())
    
    def get_status_badge_class(self):
        status_classes = {
            'pending': 'bg-warning text-dark',
            'active': 'bg-success',
            'paused': 'bg-info',
            'cancelled': 'bg-danger',
            'completed': 'bg-secondary'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_status_icon(self):
        status_icons = {
            'pending': 'bi-clock',
            'active': 'bi-check-circle',
            'paused': 'bi-pause-circle',
            'cancelled': 'bi-x-circle',
            'completed': 'bi-check-square'
        }
        return status_icons.get(self.status, 'bi-circle')
    
    def can_be_cancelled(self):
        return self.status in ['pending', 'active', 'paused']
    
    def can_be_approved(self):
        return self.status == 'pending'
    
    def can_be_paused(self):
        return self.status == 'active'
    
    def approve(self, approved_by_user_id):
        if not self.can_be_approved():
            raise ValueError("Enrollment cannot be approved in its current status")
        
        self.status = 'active'
        self.approved_by = approved_by_user_id
        self.approved_at = datetime.utcnow()
        
        if not self.monthly_fee:
            self.monthly_fee = self.calculate_monthly_fee()
        
        if not self.next_payment_due:
            from datetime import date, timedelta
            import calendar
            
            today = date.today()
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            
            last_day = calendar.monthrange(next_month.year, next_month.month)[1]
            self.next_payment_due = next_month.replace(day=last_day)
    
    def cancel(self, reason=None):
        if not self.can_be_cancelled():
            raise ValueError("Enrollment cannot be cancelled in its current status")
        
        self.status = 'cancelled'
        if reason:
            self.notes = f"{self.notes or ''}\nCancelled: {reason}".strip()
    
    def pause(self, reason=None):
        if not self.can_be_paused():
            raise ValueError("Enrollment cannot be paused in its current status")
        
        self.status = 'paused'
        if reason:
            self.notes = f"{self.notes or ''}\nPaused: {reason}".strip()
    
    def resume(self):
        if self.status != 'paused':
            raise ValueError("Only paused enrollments can be resumed")
        
        self.status = 'active'
    
    def get_attendance_summary(self):
        if not hasattr(self, 'attendance_records'):
            return {
                'total': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'excused': 0,
                'rate': 0
            }
        
        total = len(self.attendance_records)
        present = len([a for a in self.attendance_records if a.status == 'present'])
        absent = len([a for a in self.attendance_records if a.status == 'absent'])
        late = len([a for a in self.attendance_records if a.status == 'late'])
        excused = len([a for a in self.attendance_records if a.status == 'excused'])
        
        rate = (present / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'rate': round(rate, 1)
        }
    
    def __repr__(self):
        return f'<Enrollment {self.child.name} in {self.schedule.program.name} ({self.status})>'


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollment.id'), nullable=False)
    class_date = db.Column(db.Date, nullable=False)
    
    status = db.Column(db.String(20), default='present')  
    notes = db.Column(db.Text)  
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    enrollment = db.relationship('Enrollment', backref=db.backref('attendance_records', lazy=True))
    
    def get_status_display(self):
        status_map = {
            'present': 'Present',
            'absent': 'Absent',
            'late': 'Late',
            'excused': 'Excused'
        }
        return status_map.get(self.status, self.status.title())
    
    def get_status_badge_class(self):
        status_classes = {
            'present': 'bg-success',
            'absent': 'bg-danger',
            'late': 'bg-warning',
            'excused': 'bg-info'
        }
        return status_classes.get(self.status, 'bg-secondary')

    def __repr__(self):
        return f'<Attendance {self.enrollment.child.name} - {self.class_date} ({self.status})>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  
    is_read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(255))  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    
    def get_type_icon(self):
        type_icons = {
            'info': 'bi-info-circle',
            'warning': 'bi-exclamation-triangle',
            'success': 'bi-check-circle',
            'error': 'bi-x-circle'
        }
        return type_icons.get(self.type, 'bi-bell')
    
    def get_type_class(self):
        type_classes = {
            'info': 'text-info',
            'warning': 'text-warning',
            'success': 'text-success',
            'error': 'text-danger'
        }
        return type_classes.get(self.type, 'text-secondary')

    def __repr__(self):
        return f'<Notification {self.title} for {self.user.name}>'