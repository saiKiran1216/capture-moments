import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from functools import wraps
import secrets
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///capture_moments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_photographer = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Photographer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text)
    specialty = db.Column(db.String(120))
    price_per_hour = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(120))
    bookings = db.relationship('Booking', backref='photographer', lazy=True)
    reviews = db.relationship('Review', backref='photographer', lazy=True)
    profile_image = db.Column(db.String(256), nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photographer_id = db.Column(db.Integer, db.ForeignKey('photographer.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in hours
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photographer_id = db.Column(db.Integer, db.ForeignKey('photographer.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if role:
                if role == 'photographer' and not session.get('is_photographer'):
                    flash('Access denied.', 'danger')
                    return redirect(url_for('home'))
                if role == 'client' and session.get('is_photographer'):
                    flash('Access denied.', 'danger')
                    return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes will be added here

@app.context_processor
def inject_current_year():
    from datetime import datetime
    return {'current_year': datetime.now().year}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/photographers')
def show_photographers():
    # Placeholder data for demonstration
    photographers = []
    return render_template('photographers.html', photographers=photographers)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Here you would handle the form submission (e.g., send email or store message)
        flash('Thank you for contacting us! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/profile/<int:photographer_id>')
def profile(photographer_id):
    photographer = Photographer.query.get_or_404(photographer_id)
    return render_template('profile.html', photographer=photographer)

@app.route('/booking/<int:photographer_id>', methods=['GET', 'POST'])
def booking(photographer_id):
    photographer = Photographer.query.get_or_404(photographer_id)
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please log in to book a photographer.', 'warning')
            return redirect(url_for('login'))
        date = request.form['date']
        time = request.form['time']
        duration = int(request.form['duration'])
        booking = Booking(
            user_id=session['user_id'],
            photographer_id=photographer.id,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            time=datetime.strptime(time, '%H:%M').time(),
            duration=duration,
            status='confirmed'
        )
        db.session.add(booking)
        db.session.commit()
        flash('Booking successful!', 'success')
        return redirect(url_for('client_dashboard'))
    return render_template('booking.html', photographer=photographer, booking=None)

@app.route('/booking/<int:booking_id>/accept', methods=['POST'])
@login_required(role='photographer')
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    photographer = Photographer.query.filter_by(user_id=session['user_id']).first()
    if not photographer or booking.photographer_id != photographer.id:
        abort(403)
    if booking.status == 'pending':
        booking.status = 'accepted'
        db.session.commit()
        flash('Booking accepted.', 'success')
    else:
        flash('Booking cannot be accepted.', 'warning')
    return redirect(url_for('photographer_dashboard'))

@app.route('/booking/<int:booking_id>/reject', methods=['POST'])
@login_required(role='photographer')
def reject_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    photographer = Photographer.query.filter_by(user_id=session['user_id']).first()
    if not photographer or booking.photographer_id != photographer.id:
        abort(403)
    if booking.status == 'pending':
        booking.status = 'rejected'
        db.session.commit()
        flash('Booking rejected.', 'info')
    else:
        flash('Booking cannot be rejected.', 'warning')
    return redirect(url_for('photographer_dashboard'))

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required(role='photographer')
def edit_profile():
    photographer = Photographer.query.filter_by(user_id=session['user_id']).first()
    if not photographer:
        flash('Photographer profile not found.', 'danger')
        return redirect(url_for('photographer_dashboard'))
    if request.method == 'POST':
        photographer.name = request.form['name']
        photographer.specialty = request.form['specialty']
        photographer.location = request.form['location']
        photographer.price_per_hour = float(request.form['price_per_hour'])
        photographer.bio = request.form['bio']
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_name = secrets.token_hex(8) + '_' + filename
                img_dir = os.path.join('static', 'img')
                os.makedirs(img_dir, exist_ok=True)
                file.save(os.path.join(img_dir, unique_name))
                photographer.profile_image = unique_name
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('photographer_dashboard'))
    return render_template('edit_profile.html', photographer=photographer)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form.get('user_type')
        is_photographer = user_type == 'photographer'
        user = User(username=username, email=email, is_photographer=is_photographer)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
            if is_photographer:
                photographer = Photographer(user_id=user.id, name=username, price_per_hour=100.0)
                db.session.add(photographer)
                db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_photographer'] = user.is_photographer
            flash('Logged in successfully!', 'success')
            if user.is_photographer:
                return redirect(url_for('photographer_dashboard'))
            else:
                return redirect(url_for('client_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard/photographer')
@login_required(role='photographer')
def photographer_dashboard():
    photographer = Photographer.query.filter_by(user_id=session['user_id']).first()
    bookings = Booking.query.filter_by(photographer_id=photographer.id).all() if photographer else []
    return render_template('photographer_dashboard.html', photographer=photographer, bookings=bookings)

@app.route('/dashboard/client')
@login_required(role='client')
def client_dashboard():
    photographers = Photographer.query.all()
    my_bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    return render_template('client_dashboard.html', photographers=photographers, my_bookings=my_bookings)

@app.route('/my_bookings')
@login_required()
def my_bookings():
    if session.get('is_photographer'):
        photographer = Photographer.query.filter_by(user_id=session['user_id']).first()
        bookings = Booking.query.filter_by(photographer_id=photographer.id).all() if photographer else []
    else:
        bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    return render_template('my_bookings.html', bookings=bookings)

# --- TEMPORARY: Create all tables if they do not exist ---
with app.app_context():
    db.create_all()
# --- End TEMPORARY ---

if __name__ == '__main__':
    app.run(debug=True) 