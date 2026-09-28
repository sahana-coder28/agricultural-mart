from flask import Blueprint, render_template, redirect, url_for, flash, request
import re
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db, bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('user_email')
        password = request.form.get('user_password')
        role = request.form.get('role', 'customer') # Can be 'farmer' or 'admin' later

        if not re.match(r"^[A-Za-z\s]+$", username):
            flash('Warning: Name should accept only letters.', 'danger')
            return redirect(url_for('auth.register'))

        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password):
            flash('Warning: Password must contain at least one uppercase, lowercase, number, and special symbol.', 'danger')
            return redirect(url_for('auth.register'))

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Warning: Email already exists.', 'danger')
            return redirect(url_for('auth.register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password_hash=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        email = request.form.get('user_email')
        password = request.form.get('user_password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Logged in successfully.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
