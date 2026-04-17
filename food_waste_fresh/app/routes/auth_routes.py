from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.db import mysql

auth_bp = Blueprint('auth', __name__)

# Landing Page
@auth_bp.route('/')
def landing():
    return render_template('landing.html')

# Register
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()

        try:
            cur.execute(
                "INSERT INTO users (full_name, email, password, role) VALUES (%s, %s, %s, %s)",
                (full_name, email, hashed_password, role)
            )
            mysql.connection.commit()
            flash("Account created successfully. Please login.", "success")
            return redirect(url_for('auth.login'))

        except Exception:
            mysql.connection.rollback()
            flash("Email already registered.", "danger")

        finally:
            cur.close()

    return render_template('auth/register.html')

# Login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, full_name, password, role FROM users WHERE email=%s",
            (email,)
        )
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[3]

            #  ROLE-BASED REDIRECT
            if user[3] == 'donor':
                return redirect(url_for('donor.dashboard'))
            elif user[3] == 'ngo':
                return redirect(url_for('ngo.dashboard'))
            elif user[3] == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('auth.landing'))

        flash("Invalid email or password", "danger")

    return render_template('auth/login.html')



# Logout
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.landing'))

