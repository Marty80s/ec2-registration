"""Flask registration assignment. Uploaded bytes are stored in SQLite."""
import io
import os
import re
import secrets
import sqlite3
from pathlib import Path
from functools import wraps
from flask import Flask, abort, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(DATABASE=str(Path(app.instance_path) / 'users.db'),
                      MAX_CONTENT_LENGTH=2 * 1024 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config.get('SECRET_KEY'):
        key_path = Path(app.instance_path) / 'secret.key'
        try:
            with key_path.open('x') as key_file:
                os.chmod(key_path, 0o600)
                key_file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config['SECRET_KEY'] = key_path.read_text().strip()

    def connect():
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn

    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            firstname TEXT NOT NULL, lastname TEXT NOT NULL,
            email TEXT NOT NULL, address TEXT NOT NULL,
            filename TEXT, file_data BLOB, word_count INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_hex(32)
        return session['csrf']
    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.before_request
    def protect_forms():
        if request.method == 'POST':
            if not secrets.compare_digest(session.get('csrf', ''), request.form.get('csrf', '')) or 'csrf' not in session:
                abort(400, 'Form expired. Reload the page and try again.')

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    @app.route('/', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            values = {k: request.form.get(k, '').strip() for k in
                      ('username', 'firstname', 'lastname', 'email', 'address')}
            password = request.form.get('password', '')
            error = None
            if not all(values.values()) or not password:
                error = 'Please complete every required field.'
            elif not re.fullmatch(r'[A-Za-z0-9_.-]{3,40}', values['username']):
                error = 'Use 3–40 letters, numbers, dots, hyphens, or underscores for your username.'
            elif not 8 <= len(password) <= 256:
                error = 'Use a password between 8 and 256 characters.'
            elif any(len(v) > 500 for v in values.values()):
                error = 'Each detail must be 500 characters or fewer.'
            elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']):
                error = 'Please enter a valid email address.'
            upload = request.files.get('document')
            filename, data, count = None, None, None
            if upload and upload.filename:
                filename = secure_filename(upload.filename)
                if not filename.lower().endswith('.txt'):
                    error = 'Choose a .txt file.'
                else:
                    data = upload.read()
                    try:
                        content = data.decode('utf-8-sig')
                        if '\x00' in content:
                            raise ValueError()
                        count = len(content.split())
                    except (UnicodeDecodeError, ValueError):
                        error = 'Choose a UTF-8 plain text file.'
            if error:
                flash(error, 'error')
                return render_template('register.html'), 400
            try:
                with connect() as db:
                    cursor = db.execute('''INSERT INTO users
                        (username, password_hash, firstname, lastname, email, address, filename, file_data, word_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (values['username'], generate_password_hash(password), values['firstname'],
                         values['lastname'], values['email'], values['address'], filename, data, count))
                    user_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                flash('That username is already registered. Choose another or log in.', 'error')
                return render_template('register.html'), 409
            session.clear()
            session['user_id'] = user_id
            flash('Registration complete. Your details have been saved.', 'success')
            return redirect(url_for('profile'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            with connect() as db:
                user = db.execute('SELECT id, password_hash FROM users WHERE username=?',
                                  (request.form.get('username', '').strip(),)).fetchone()
            if user and check_password_hash(user['password_hash'], request.form.get('password', '')):
                session.clear()
                session['user_id'] = user['id']
                return redirect(url_for('profile'))
            flash('Incorrect username or password. Please try again.', 'error')
            return render_template('login.html'), 401
        return render_template('login.html')

    @app.get('/profile')
    @login_required
    def profile():
        with connect() as db:
            user = db.execute('''SELECT username, firstname, lastname, email, address,
                              filename, word_count FROM users WHERE id=?''', (session['user_id'],)).fetchone()
        if user is None:
            session.clear()
            return redirect(url_for('login'))
        return render_template('profile.html', user=user)

    @app.get('/download')
    @login_required
    def download():
        with connect() as db:
            row = db.execute('SELECT filename, file_data FROM users WHERE id=?', (session['user_id'],)).fetchone()
        if row is None or row['file_data'] is None:
            abort(404)
        return send_file(io.BytesIO(row['file_data']), mimetype='text/plain',
                         as_attachment=True, download_name=row['filename'])

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.errorhandler(413)
    def too_large(error):
        return render_template('error.html', message='Upload too large. Choose a text file smaller than 1 MB.'), 413

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000)
