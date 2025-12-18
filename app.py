# app.py - UPDATED
from flask import Flask, render_template, redirect, url_for, flash, jsonify, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Court, Equipment, Coach, Booking, BookingEquipment, PricingRule
from database import init_db, seed_data
import json
from datetime import datetime, date
from decorators import admin_required  # Import from decorators
from admin import admin_bp



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///courtbook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and login manager
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.register_blueprint(admin_bp)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
@login_required
def home():
    return render_template('home.html', user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return jsonify({'success': True, 'message': 'Login successful', 'is_admin': user.is_admin})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'})

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'})

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'})

        # First user becomes admin
        is_admin = User.query.count() == 0

        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return jsonify({'success': True, 'message': 'Registration successful', 'is_admin': user.is_admin})

    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Remove the duplicate admin_dashboard route here since it's in admin.py
# The blueprint handles the /admin route


# API Routes
@app.route('/api/courts')
@login_required
def get_courts():
    courts = Court.query.all()
    return jsonify([{
        'id': court.id,
        'name': court.name,
        'type': court.type,
        'base_price': court.base_price
    } for court in courts])


@app.route('/api/equipment')
@login_required
def get_equipment():
    equipment = Equipment.query.all()
    return jsonify([{
        'id': eq.id,
        'name': eq.name,
        'price': eq.price,
        'available': eq.total_available
    } for eq in equipment])


@app.route('/api/coaches')
@login_required
def get_coaches():
    coaches = Coach.query.all()
    return jsonify([{
        'id': coach.id,
        'name': coach.name,
        'price': coach.price,
        'specialization': coach.specialization
    } for coach in coaches])


@app.route('/api/timeslots')
@login_required
def get_timeslots():
    time_slots = [
        '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
        '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
        '18:00', '19:00', '20:00', '21:00'
    ]
    return jsonify(time_slots)


@app.route('/api/pricing_rules')
@login_required
def get_pricing_rules():
    # Get all enabled pricing rules
    rules = PricingRule.query.filter_by(enabled=True).all()
    # Convert to frontend format
    rules_dict = {}
    for rule in rules:
        if rule.rule_type == 'peak_hours':
            rules_dict['peakHours'] = {
                'enabled': rule.enabled,
                'multiplier': rule.multiplier,
                'start': rule.start_time or '18:00',
                'end': rule.end_time or '21:00'
            }
        elif rule.rule_type == 'weekend':
            rules_dict['weekend'] = {
                'enabled': rule.enabled,
                'multiplier': rule.multiplier
            }
        elif rule.rule_type == 'indoor':
            rules_dict['indoor'] = {
                'enabled': rule.enabled,
                'multiplier': rule.multiplier
            }
        elif rule.rule_type == 'multiple_hours':
            rules_dict['multipleHours'] = {
                'enabled': rule.enabled,
                'discountPerHour': rule.discount
            }
        elif rule.rule_type == 'bundle':
            rules_dict['bundle'] = {
                'enabled': rule.enabled,
                'discount': rule.discount,
                'minItems': rule.min_items or 3
            }

    return jsonify(rules_dict)


@app.route('/api/bookings', methods=['GET', 'POST'])
@login_required
def handle_bookings():
    if request.method == 'GET':
        # Get user's booking history
        bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.date.desc()).all()

        booking_list = []
        for booking in bookings:
            # Get equipment for this booking
            booking_equipment = BookingEquipment.query.filter_by(booking_id=booking.id).all()
            equipment_details = []
            for be in booking_equipment:
                eq = Equipment.query.get(be.equipment_id)
                equipment_details.append({
                    'name': eq.name,
                    'quantity': be.quantity,
                    'price': eq.price
                })

            # Get coach details
            coach_details = None
            if booking.coach_id:
                coach = Coach.query.get(booking.coach_id)
                coach_details = {
                    'name': coach.name,
                    'price': coach.price
                }

            booking_list.append({
                'id': booking.id,
                'date': booking.date.strftime('%Y-%m-%d'),
                'time_slot': booking.time_slot,
                'court': {
                    'name': booking.court.name,
                    'type': booking.court.type,
                    'base_price': booking.court.base_price
                },
                'equipment': equipment_details,
                'coach': coach_details,
                'total_price': booking.total_price
            })

        return jsonify(booking_list)

    elif request.method == 'POST':
        # Create new booking
        data = request.get_json()

        # Validate booking data
        court = Court.query.get(data['court']['id'])
        if not court:
            return jsonify({'success': False, 'message': 'Court not found'})

        # Check if court is available for this timeslot
        existing_booking = Booking.query.filter_by(
            court_id=court.id,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            time_slot=data['timeSlot']
        ).first()

        if existing_booking:
            return jsonify({'success': False, 'message': 'Court already booked for this timeslot'})

        # Check coach availability
        coach = None
        if data.get('coach'):
            coach = Coach.query.get(data['coach']['id'])
            if coach:
                # Check if coach is already booked
                coach_booking = Booking.query.filter_by(
                    coach_id=coach.id,
                    date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                    time_slot=data['timeSlot']
                ).first()

                if coach_booking:
                    return jsonify({'success': False, 'message': 'Coach already booked for this timeslot'})

        # Create booking
        booking = Booking(
            user_id=current_user.id,
            court_id=court.id,
            coach_id=coach.id if coach else None,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            time_slot=data['timeSlot'],
            total_price=data['totalPrice']
        )

        db.session.add(booking)
        db.session.commit()

        # Add equipment to booking
        for equip_id, quantity in data['equipment'].items():
            equipment = Equipment.query.get(int(equip_id))
            if equipment and quantity > 0:
                booking_eq = BookingEquipment(
                    booking_id=booking.id,
                    equipment_id=equipment.id,
                    quantity=quantity
                )
                db.session.add(booking_eq)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Booking confirmed!', 'booking_id': booking.id})


@app.route('/api/check_availability')
@login_required
def check_availability():
    selected_date = request.args.get('date')
    selected_time = request.args.get('time')

    if not selected_date:
        return jsonify({})

    # Get booked courts for this date and time
    booked_courts = Booking.query.filter_by(
        date=datetime.strptime(selected_date, '%Y-%m-%d').date()
    )

    if selected_time:
        booked_courts = booked_courts.filter_by(time_slot=selected_time)

    booked_courts = booked_courts.all()

    booked_court_ids = [b.court_id for b in booked_courts]
    booked_coach_ids = [b.coach_id for b in booked_courts if b.coach_id]

    # Get equipment availability
    equipment = Equipment.query.all()
    equipment_availability = {}

    for eq in equipment:
        # Start with total available
        available = eq.total_available

        if selected_time:
            # Get total booked quantity for this equipment at this specific time
            total_booked = 0
            bookings_with_slot = Booking.query.filter_by(
                date=datetime.strptime(selected_date, '%Y-%m-%d').date(),
                time_slot=selected_time
            ).all()

            for booking in bookings_with_slot:
                booking_eq = BookingEquipment.query.filter_by(
                    booking_id=booking.id,
                    equipment_id=eq.id
                ).first()

                if booking_eq:
                    total_booked += booking_eq.quantity

            available = eq.total_available - total_booked

        equipment_availability[eq.id] = max(0, available)

    return jsonify({
        'booked_courts': booked_court_ids,
        'booked_coaches': booked_coach_ids,
        'equipment_availability': equipment_availability
    })


@app.route('/api/admin/seed', methods=['POST'])
@login_required
@admin_required
def seed_admin_data():
    """Seed additional data (admin only)"""
    try:
        seed_data()
        return jsonify({'success': True, 'message': 'Database seeded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/backup', methods=['GET'])
@login_required
@admin_required
def backup_database():
    """Create database backup (admin only)"""
    try:
        backup_path = f'backup_courtbook_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        # This is a simple backup - in production, use proper backup methods
        import shutil
        shutil.copy2('courtbook.db', backup_path)
        return jsonify({'success': True, 'message': f'Backup created: {backup_path}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)