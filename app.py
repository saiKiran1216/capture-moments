import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from functools import wraps
import secrets
from werkzeug.utils import secure_filename
import boto3
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///capture_moments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# AWS DynamoDB Configuration
app.config['AWS_REGION'] = os.environ.get('AWS_REGION', 'ap-south-1')
app.config['USE_AWS'] = os.environ.get('USE_AWS', 'false').lower() == 'true'

db = SQLAlchemy(app)

# Initialize DynamoDB if AWS is enabled
if app.config['USE_AWS']:
    try:
        dynamodb = boto3.resource('dynamodb', region_name=app.config['AWS_REGION'])
        photographers_table = dynamodb.Table('photographers')
        bookings_table = dynamodb.Table('booking')
        users_table = dynamodb.Table('users')
        print("✅ AWS DynamoDB connected successfully!")
    except Exception as e:
        print(f"⚠️ AWS DynamoDB connection failed: {e}")
        print("Falling back to SQLite database...")
        app.config['USE_AWS'] = False
else:
    print("📁 Using local SQLite database")

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

# AWS DynamoDB Helper Functions
def get_photographers_from_dynamodb():
    """Get all photographers from DynamoDB"""
    if not app.config['USE_AWS']:
        return []
    try:
        response = photographers_table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error fetching photographers from DynamoDB: {e}")
        return []

def save_booking_to_dynamodb(user_id, photographer_id, date, time, duration, status='pending'):
    """Save booking to DynamoDB"""
    if not app.config['USE_AWS']:
        return None
    try:
        booking_id = str(uuid.uuid4())
        booking_item = {
            'booking_id': booking_id,
            'user_id': str(user_id),
            'photographer_id': str(photographer_id),
            'date': date,
            'time': time,
            'duration': duration,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        bookings_table.put_item(Item=booking_item)
        return booking_id
    except Exception as e:
        print(f"Error saving booking to DynamoDB: {e}")
        return None

def save_user_to_dynamodb(username, email, password_hash, is_photographer=False):
    """Save user to DynamoDB"""
    if not app.config['USE_AWS']:
        return None
    try:
        user_id = str(uuid.uuid4())
        user_item = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'is_photographer': is_photographer,
            'created_at': datetime.now().isoformat()
        }
        users_table.put_item(Item=user_item)
        print(f"✅ User saved to DynamoDB: {username}")
        return user_id
    except Exception as e:
        print(f"❌ Error saving user to DynamoDB: {e}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        return None

def get_user_from_dynamodb(username):
    """Get user from DynamoDB by username"""
    if not app.config['USE_AWS']:
        return None
    try:
        response = users_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('username').eq(username)
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"Error fetching user from DynamoDB: {e}")
        return None

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
    if app.config['USE_AWS']:
        # Get photographers from DynamoDB
        photographers = get_photographers_from_dynamodb()
        # Convert DynamoDB format to template-compatible format
        formatted_photographers = []
        for p in photographers:
            formatted_photographers.append({
                'id': p.get('photographer_id'),
                'name': p.get('Name', 'Unknown'),
                'specialty': p.get('Skills', 'General'),
                'location': p.get('Location', 'Not specified'),
                'price_per_hour': p.get('price_per_hour', 100.0),
                'profile_image': p.get('Photo')
            })
    else:
        # Get photographers from SQLite
        photographers = Photographer.query.all()
        formatted_photographers = photographers
    
    return render_template('photographers.html', photographers=formatted_photographers)

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
    if app.config['USE_AWS']:
        # Get photographer from DynamoDB
        photographers = get_photographers_from_dynamodb()
        photographer = None
        for p in photographers:
            if p.get('photographer_id') == str(photographer_id):
                photographer = {
                    'id': p.get('photographer_id'),
                    'name': p.get('Name', 'Unknown'),
                    'specialty': p.get('Skills', 'General'),
                    'location': p.get('Location', 'Not specified'),
                    'price_per_hour': p.get('price_per_hour', 100.0),
                    'profile_image': p.get('Photo')
                }
                break
        if not photographer:
            abort(404)
    else:
        # Get photographer from SQLite
        photographer = Photographer.query.get_or_404(photographer_id)
    
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please log in to book a photographer.', 'warning')
            return redirect(url_for('login'))
        
        date = request.form['date']
        time = request.form['time']
        duration = int(request.form['duration'])
        
        if app.config['USE_AWS']:
            # Save to DynamoDB
            booking_id = save_booking_to_dynamodb(
                session['user_id'], 
                photographer_id, 
                date, 
                time, 
                duration, 
                'confirmed'
            )
            if booking_id:
                flash('Booking successful!', 'success')
            else:
                flash('Booking failed. Please try again.', 'danger')
        else:
            # Save to SQLite
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
        
        if app.config['USE_AWS']:
            try:
                # Check if user exists in DynamoDB
                existing_user = get_user_from_dynamodb(username)
                if existing_user:
                    flash('Username or email already exists.', 'danger')
                    return render_template('signup.html')
                
                # Create user in DynamoDB
                password_hash = generate_password_hash(password)
                user_id = save_user_to_dynamodb(username, email, password_hash, is_photographer)
                
                if user_id:
                    flash('Account created successfully! Please log in.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('Account creation failed. Please try again.', 'danger')
            except Exception as e:
                print(f"❌ Signup error: {e}")
                flash(f'Account creation failed: {str(e)}', 'danger')
        else:
            # Create user in SQLite
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
        
        if app.config['USE_AWS']:
            # Get user from DynamoDB
            user_data = get_user_from_dynamodb(username)
            if user_data and check_password_hash(user_data['password_hash'], password):
                session['user_id'] = user_data['user_id']
                session['username'] = user_data['username']
                session['is_photographer'] = user_data['is_photographer']
                flash('Logged in successfully!', 'success')
                if user_data['is_photographer']:
                    return redirect(url_for('photographer_dashboard'))
                else:
                    return redirect(url_for('client_dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        else:
            # Get user from SQLite
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

# AWS Integration Routes (similar to awsint.py)
@app.route('/aws/book', methods=['GET', 'POST'])
def aws_book():
    """AWS-specific booking route (no authentication required)"""
    if request.method == 'POST':
        photographer_id = request.form.get('photographer_id')
        user_id = request.form.get('user_id')
        date = request.form.get('date')

        if app.config['USE_AWS']:
            # Create unique booking ID
            booking_id = str(uuid.uuid4())
            
            # Store booking in DynamoDB
            try:
                bookings_table.put_item(Item={
                    'booking_id': booking_id,
                    'photographer_id': photographer_id,
                    'user_id': user_id,
                    'date': date,
                    'timestamp': datetime.now().isoformat()
                })
                return f"<h2 style='color:green;'>Booking Confirmed! For {photographer_id} on {date}.</h2><a href='/'>Back to Home</a>"
            except Exception as e:
                return f"<h2 style='color:red;'>Booking Failed: {e}</h2><a href='/'>Back to Home</a>"
        else:
            return "<h2 style='color:red;'>AWS mode is disabled. Use regular booking.</h2><a href='/'>Back to Home</a>"

    return render_template('book.html')

@app.route('/aws/show-photographers')
def aws_show_photographers():
    """AWS-specific photographers route"""
    if app.config['USE_AWS']:
        photographers = get_photographers_from_dynamodb()
        availability_data = {
            p['photographer_id']: p.get('availability', []) for p in photographers
        }
        return render_template('photographers.html',
                               photographers=photographers,
                               availability_data=availability_data)
    else:
        flash('AWS mode is disabled. Use regular photographers page.', 'warning')
        return redirect(url_for('show_photographers'))

# --- TEMPORARY: Create all tables if they do not exist ---
with app.app_context():
    db.create_all()
# --- End TEMPORARY ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)