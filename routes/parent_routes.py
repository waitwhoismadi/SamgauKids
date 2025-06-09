from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from database import db
from models import Parent, Center, Child, Category, Enrollment
from utils import login_required, save_uploaded_file

parent_bp = Blueprint('parent', __name__)

@parent_bp.route('/dashboard')
@login_required(role='parent')
def dashboard():
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

@parent_bp.route('/children')
@login_required(role='parent')
def manage_children():
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    children = Child.query.filter_by(parent_id=parent.id).all() if parent else []
    
    return render_template('parent/children.html', children=children)

@parent_bp.route('/children/add', methods=['GET', 'POST'])
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
            return redirect(url_for('parent.manage_children'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding child. Please try again.', 'danger')
    
    return render_template('parent/add_child.html')

@parent_bp.route('/children/<int:child_id>/edit', methods=['GET', 'POST'])
@login_required(role='parent')
def edit_child(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        flash('Child not found.', 'danger')
        return redirect(url_for('parent.manage_children'))
    
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
            return redirect(url_for('parent.manage_children'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating child. Please try again.', 'danger')
    
    return render_template('parent/edit_child.html', child=child)

@parent_bp.route('/children/<int:child_id>/delete', methods=['POST'])
@login_required(role='parent')
def delete_child(child_id):
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    child = Child.query.filter_by(id=child_id, parent_id=parent.id).first()
    
    if not child:
        flash('Child not found.', 'danger')
        return redirect(url_for('parent.manage_children'))
    
    try:
        active_enrollments = Enrollment.query.filter_by(child_id=child.id, status='active').count()
        if active_enrollments > 0:
            flash(f'Cannot delete {child.name}. Please cancel all active enrollments first.', 'danger')
            return redirect(url_for('parent.manage_children'))
        
        child_name = child.name
        db.session.delete(child)
        db.session.commit()
        flash(f'{child_name} has been removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting child. Please try again.', 'danger')
    
    return redirect(url_for('parent.manage_children'))

@parent_bp.route('/enrollments')
@login_required(role='parent')
def enrollments():
    parent = Parent.query.filter_by(user_id=session['user_id']).first()
    
    enrollments = db.session.query(Enrollment).join(Child).filter(
        Child.parent_id == parent.id
    ).order_by(Enrollment.created_at.desc()).all() if parent else []
    
    return render_template('parent/enrollments.html',
                         parent=parent,
                         enrollments=enrollments)