from flask import Flask, render_template, request, jsonify
import boto3
import uuid
from datetime import datetime

# Step 1: Create the Flask app instance
app = Flask(__name__)

# Step 2: Connect to DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')  # Replace with your region

# Tables
photographers_table = dynamodb.Table('photographers')
bookings_table = dynamodb.Table('booking')

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Booking form route
@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        photographer_id = request.form.get('photographer_id')
        user_id = request.form.get('user_id')
        date = request.form.get('date')

        # Create unique booking ID
        booking_id = str(uuid.uuid4())

        # Store booking in DynamoDB Bookings table
        bookings_table.put_item(Item={
            'booking_id': booking_id,
            'photographer_id': photographer_id,
            'user_id': user_id,
            'date': date,
            'timestamp': datetime.now().isoformat()
        })

        return f"<h2 style='color:green;'>Booking Confirmed! For {photographer_id} on {date}.</h2><a href='/'>Back to Home</a>"

    return render_template('book.html')

# Display photographers from DynamoDB
@app.route('/show-photographers')
def show_photographers():
    response = photographers_table.scan()
    photographers = response.get('Items', [])

    # ✅ FIXED: use correct DynamoDB key - 'photographer_id'
    availability_data = {
        p['photographer_id']: p.get('availability', []) for p in photographers
    }

    return render_template('photographers.html',
                           photographers=photographers,
                           availability_data=availability_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
