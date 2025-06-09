from flask import current_app, render_template, url_for
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import threading
from datetime import datetime

class EmailService:
    def __init__(self, app=None):
        self.mail = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.mail = Mail(app)
    
    def send_async_email(self, app, msg):
        with app.app_context():
            try:
                self.mail.send(msg)
            except Exception as e:
                current_app.logger.error(f'Failed to send email: {str(e)}')
    
    def send_email(self, to, subject, template, **kwargs):
        app = current_app._get_current_object()
        
        msg = Message(
            subject=current_app.config['MAIL_SUBJECT_PREFIX'] + subject,
            recipients=[to],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
        kwargs['base_url'] = base_url
        
        try:
            msg.html = render_template(f'emails/{template}.html', **kwargs)
            try:
                msg.body = render_template(f'emails/{template}.txt', **kwargs)
            except:
                pass
        except Exception as e:
            current_app.logger.error(f'Template error: {str(e)}')
            raise
        
        thread = threading.Thread(
            target=self.send_async_email,
            args=[app, msg]
        )
        thread.start()
        return thread
    
    def generate_reset_token(self, email):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(email, salt=current_app.config['RESET_PASSWORD_SALT'])
    
    def verify_reset_token(self, token, expiration=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = s.loads(
                token,
                salt=current_app.config['RESET_PASSWORD_SALT'],
                max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None
    
    def _get_base_url(self):
        return current_app.config.get('BASE_URL', 'http://localhost:5000')
    
    def send_welcome_email(self, user, role):
        base_url = self._get_base_url()
        login_url = f"{base_url}/auth/login"
        
        return self.send_email(
            to=user.email,
            subject='Welcome to EduPlatform!',
            template='welcome',
            user=user,
            role=role,
            login_url=login_url
        )
    
    def send_password_reset_email(self, user):
        token = self.generate_reset_token(user.email)
        base_url = self._get_base_url()
        reset_url = f"{base_url}/auth/reset-password/{token}"
        
        return self.send_email(
            to=user.email,
            subject='Password Reset Request',
            template='password_reset',
            user=user,
            reset_url=reset_url,
            expiration_hours=1
        )
    
    def send_enrollment_confirmation(self, enrollment):
        parent_email = enrollment.child.parent.user.email
        
        return self.send_email(
            to=parent_email,
            subject='Enrollment Confirmation',
            template='enrollment_confirmation',
            enrollment=enrollment,
            child=enrollment.child,
            program=enrollment.schedule.program,
            center=enrollment.schedule.program.center,
            parent=enrollment.child.parent.user
        )
    
    def send_enrollment_notification_to_center(self, enrollment):
        center_email = enrollment.schedule.program.center.user.email
        base_url = self._get_base_url()
        approve_url = f"{base_url}/center/enrollments"
        
        return self.send_email(
            to=center_email,
            subject='New Enrollment Request',
            template='enrollment_notification_center',
            enrollment=enrollment,
            child=enrollment.child,
            program=enrollment.schedule.program,
            center=enrollment.schedule.program.center,
            parent=enrollment.child.parent.user,
            approve_url=approve_url
        )
    
    def send_enrollment_approved(self, enrollment):
        parent_email = enrollment.child.parent.user.email
        
        return self.send_email(
            to=parent_email,
            subject='Enrollment Approved!',
            template='enrollment_approved',
            enrollment=enrollment,
            child=enrollment.child,
            program=enrollment.schedule.program,
            center=enrollment.schedule.program.center,
            schedule=enrollment.schedule
        )
    
    def send_class_reminder(self, enrollment, class_date):
        parent_email = enrollment.child.parent.user.email
        
        return self.send_email(
            to=parent_email,
            subject=f'Class Reminder - {enrollment.schedule.program.name}',
            template='class_reminder',
            enrollment=enrollment,
            child=enrollment.child,
            program=enrollment.schedule.program,
            schedule=enrollment.schedule,
            class_date=class_date,
            center=enrollment.schedule.program.center
        )
    
    def send_attendance_report(self, parent, monthly_report):
        return self.send_email(
            to=parent.user.email,
            subject='Monthly Attendance Report',
            template='attendance_report',
            parent=parent,
            report=monthly_report,
            month=datetime.now().strftime('%B %Y')
        )
    
    def send_teacher_assignment_notification(self, teacher, program):
        return self.send_email(
            to=teacher.user.email,
            subject='New Program Assignment',
            template='teacher_assignment',
            teacher=teacher,
            program=program,
            center=teacher.center
        )
    
    def send_payment_reminder(self, enrollment):
        parent_email = enrollment.child.parent.user.email
        
        return self.send_email(
            to=parent_email,
            subject='Payment Reminder',
            template='payment_reminder',
            enrollment=enrollment,
            child=enrollment.child,
            program=enrollment.schedule.program,
            amount_due=enrollment.outstanding_balance,
            due_date=enrollment.next_payment_due
        )
    
    def send_center_invite_code(self, center):
        return self.send_email(
            to=center.user.email,
            subject='Your Teacher Invite Code',
            template='center_invite_code',
            center=center,
            invite_code=center.invite_code
        )

email_service = EmailService()