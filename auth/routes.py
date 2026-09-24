import re

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Student ID must look like 22-01234
STUDENT_ID_PATTERN = re.compile(r'^\d{2}-\d{5}$')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        customer_type = request.form.get('customer_type', 'normal')
        student_id = request.form.get('student_id', '').strip()

        errors = []
        if not full_name or not email or not password:
            errors.append('Please fill out all required fields.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with that email already exists.')

        if customer_type == 'student':
            if not STUDENT_ID_PATTERN.match(student_id):
                errors.append('Student ID must be in the format XX-XXXXX (e.g. 22-01234).')
        else:
            customer_type = 'normal'
            student_id = None

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/signup.html', form=request.form)

        user = User(
            full_name=full_name,
            email=email,
            phone_number=phone_number or None,
            password_hash=generate_password_hash(password),
            role='customer',
            customer_type=customer_type,
            student_id=student_id,
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html', form={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone_number = request.form.get('phone_number', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        errors = []

        if not full_name or not email:
            errors.append('Name and email are required.')
        existing_email = User.query.filter(
            User.email == email, User.id != current_user.id
        ).first()
        if existing_email:
            errors.append('That email address is already used by another account.')

        password_requested = bool(current_password or new_password or confirm_password)
        if password_requested:
            if not current_password or not new_password or not confirm_password:
                errors.append('Fill in all password fields to change your password.')
            elif not check_password_hash(current_user.password_hash, current_password):
                errors.append('Your current password is incorrect.')
            elif len(new_password) < 8:
                errors.append('Your new password must be at least 8 characters long.')
            elif new_password != confirm_password:
                errors.append('The new passwords do not match.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/profile.html', form=request.form)

        current_user.full_name = full_name
        current_user.email = email
        current_user.phone_number = phone_number or None
        if password_requested:
            current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', form={})
