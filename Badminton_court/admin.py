# admin.py - UPDATED
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, User, Court, Equipment, Coach, Booking, BookingEquipment, PricingRule
from decorators import admin_required  # Changed import
from datetime import datetime, date

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# Admin Dashboard Routes
@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', user=current_user)


# API Routes for Admin Data
@admin_bp.route('/api/dashboard/stats')
@login_required
@admin_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    active_bookings = Booking.query.filter(Booking.date >= date.today()).count()
    total_revenue = db.session.query(db.func.sum(Booking.total_price)).scalar() or 0

    # Today's bookings
    today_bookings = Booking.query.filter_by(date=date.today()).count()

    # Revenue by month (last 6 months)
    six_months_ago = date.today().replace(
        month=date.today().month - 6 if date.today().month > 6 else date.today().month + 6)
    monthly_revenue = db.session.query(
        db.func.strftime('%Y-%m', Booking.date),
        db.func.sum(Booking.total_price)
    ).filter(Booking.date >= six_months_ago).group_by(
        db.func.strftime('%Y-%m', Booking.date)
    ).order_by(
        db.func.strftime('%Y-%m', Booking.date).desc()
    ).limit(6).all()

    return jsonify({
        'totalUsers': total_users,
        'totalBookings': total_bookings,
        'activeBookings': active_bookings,
        'todayBookings': today_bookings,
        'totalRevenue': total_revenue,
        'monthlyRevenue': [{'month': month, 'revenue': revenue} for month, revenue in monthly_revenue]
    })


@admin_bp.route('/api/users')
@login_required
@admin_required
def get_users():
    """Get all users with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '')

    query = User.query

    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'users': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'isAdmin': user.is_admin,
            'createdAt': user.created_at.strftime('%Y-%m-%d %H:%M'),
            'totalBookings': Booking.query.filter_by(user_id=user.id).count()
        } for user in users.items],
        'total': users.total,
        'page': users.page,
        'per_page': users.per_page,
        'pages': users.pages
    })


@admin_bp.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_user(user_id):
    """Manage individual user"""
    user = User.query.get_or_404(user_id)

    if request.method == 'GET':
        user_bookings = Booking.query.filter_by(user_id=user_id).all()

        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'isAdmin': user.is_admin,
            'createdAt': user.created_at.strftime('%Y-%m-%d %H:%M'),
            'bookings': [{
                'id': booking.id,
                'date': booking.date.strftime('%Y-%m-%d'),
                'timeSlot': booking.time_slot,
                'court': booking.court.name,
                'totalPrice': booking.total_price
            } for booking in user_bookings],
            'totalSpent': sum(booking.total_price for booking in user_bookings)
        })

    elif request.method == 'PUT':
        data = request.get_json()

        # Prevent modifying yourself if you're the only admin
        if user.id == current_user.id and data.get('isAdmin') is False and User.query.filter_by(
                is_admin=True).count() == 1:
            return jsonify({'success': False, 'message': 'Cannot remove last admin'}), 400

        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'success': False, 'message': 'Username already exists'}), 400
            user.username = data['username']

        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'success': False, 'message': 'Email already exists'}), 400
            user.email = data['email']

        if 'isAdmin' in data:
            user.is_admin = data['isAdmin']

        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully'})

    elif request.method == 'DELETE':
        # Prevent deleting yourself
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400

        # Delete user's bookings first
        Booking.query.filter_by(user_id=user_id).delete()

        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})


@admin_bp.route('/api/bookings')
@login_required
@admin_required
def get_all_bookings():
    """Get all bookings with filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status', 'all')  # all, upcoming, past
    date_filter = request.args.get('date', '')
    search = request.args.get('search', '')

    query = Booking.query.join(User).join(Court)

    # Apply filters
    if status == 'upcoming':
        query = query.filter(Booking.date >= date.today())
    elif status == 'past':
        query = query.filter(Booking.date < date.today())

    if date_filter:
        query = query.filter(Booking.date == datetime.strptime(date_filter, '%Y-%m-%d').date())

    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (Court.name.ilike(f'%{search}%'))
        )

    bookings = query.order_by(Booking.date.desc(), Booking.time_slot).paginate(
        page=page, per_page=per_page, error_out=False
    )

    booking_list = []
    for booking in bookings.items:
        # Get equipment for this booking
        booking_equipment = BookingEquipment.query.filter_by(booking_id=booking.id).all()
        equipment_details = []
        for be in booking_equipment:
            eq = Equipment.query.get(be.equipment_id)
            if eq:
                equipment_details.append(f'{eq.name} x{be.quantity}')

        booking_list.append({
            'id': booking.id,
            'date': booking.date.strftime('%Y-%m-%d'),
            'timeSlot': booking.time_slot,
            'user': {
                'id': booking.user.id,
                'username': booking.user.username,
                'email': booking.user.email
            },
            'court': {
                'id': booking.court.id,
                'name': booking.court.name,
                'type': booking.court.type
            },
            'coach': booking.coach.name if booking.coach else None,
            'equipment': equipment_details,
            'totalPrice': booking.total_price,
            'createdAt': booking.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return jsonify({
        'bookings': booking_list,
        'total': bookings.total,
        'page': bookings.page,
        'per_page': bookings.per_page,
        'pages': bookings.pages
    })


@admin_bp.route('/api/bookings/<int:booking_id>', methods=['GET', 'DELETE'])
@login_required
@admin_required
def manage_booking(booking_id):
    """Get or delete a booking"""
    booking = Booking.query.get_or_404(booking_id)

    if request.method == 'GET':
        # Get equipment details
        booking_equipment = BookingEquipment.query.filter_by(booking_id=booking.id).all()
        equipment_details = []
        for be in booking_equipment:
            eq = Equipment.query.get(be.equipment_id)
            if eq:
                equipment_details.append({
                    'name': eq.name,
                    'quantity': be.quantity,
                    'price': eq.price
                })

        return jsonify({
            'id': booking.id,
            'date': booking.date.strftime('%Y-%m-%d'),
            'timeSlot': booking.time_slot,
            'user': {
                'id': booking.user.id,
                'username': booking.user.username,
                'email': booking.user.email
            },
            'court': {
                'id': booking.court.id,
                'name': booking.court.name,
                'type': booking.court.type,
                'basePrice': booking.court.base_price
            },
            'coach': {
                'id': booking.coach.id,
                'name': booking.coach.name,
                'price': booking.coach.price
            } if booking.coach else None,
            'equipment': equipment_details,
            'totalPrice': booking.total_price,
            'createdAt': booking.created_at.strftime('%Y-%m-%d %H:%M')
        })

    elif request.method == 'DELETE':
        # Delete associated equipment bookings
        BookingEquipment.query.filter_by(booking_id=booking_id).delete()

        db.session.delete(booking)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Booking deleted successfully'})


@admin_bp.route('/api/courts', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_courts():
    """Get all courts or add new court"""
    if request.method == 'GET':
        courts = Court.query.order_by(Court.name).all()
        return jsonify([{
            'id': court.id,
            'name': court.name,
            'type': court.type,
            'basePrice': court.base_price,
            'isActive': court.is_active,
            'createdAt': court.created_at.strftime('%Y-%m-%d'),
            'totalBookings': Booking.query.filter_by(court_id=court.id).count()
        } for court in courts])

    elif request.method == 'POST':
        data = request.get_json()

        # Validate required fields
        if not all(key in data for key in ['name', 'type', 'basePrice']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # Check if court name already exists
        if Court.query.filter_by(name=data['name']).first():
            return jsonify({'success': False, 'message': 'Court name already exists'}), 400

        court = Court(
            name=data['name'],
            type=data['type'],
            base_price=data['basePrice'],
            is_active=data.get('isActive', True)
        )

        db.session.add(court)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Court added successfully',
            'court': {
                'id': court.id,
                'name': court.name,
                'type': court.type,
                'basePrice': court.base_price,
                'isActive': court.is_active
            }
        })


@admin_bp.route('/api/courts/<int:court_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def manage_court(court_id):
    """Update or delete a court"""
    court = Court.query.get_or_404(court_id)

    if request.method == 'PUT':
        data = request.get_json()

        if 'name' in data and data['name'] != court.name:
            if Court.query.filter_by(name=data['name']).first():
                return jsonify({'success': False, 'message': 'Court name already exists'}), 400
            court.name = data['name']

        if 'type' in data:
            court.type = data['type']

        if 'basePrice' in data:
            court.base_price = data['basePrice']

        if 'isActive' in data:
            court.is_active = data['isActive']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Court updated successfully'})

    elif request.method == 'DELETE':
        # Check if court has bookings
        if Booking.query.filter_by(court_id=court_id).first():
            return jsonify({'success': False, 'message': 'Cannot delete court with existing bookings'}), 400

        db.session.delete(court)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Court deleted successfully'})


@admin_bp.route('/api/equipment', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_equipment():
    """Get all equipment or add new equipment"""
    if request.method == 'GET':
        equipment = Equipment.query.order_by(Equipment.name).all()
        return jsonify([{
            'id': eq.id,
            'name': eq.name,
            'price': eq.price,
            'totalAvailable': eq.total_available,
            'createdAt': eq.created_at.strftime('%Y-%m-%d'),
            'currentlyBooked': get_currently_booked_quantity(eq.id)
        } for eq in equipment])

    elif request.method == 'POST':
        data = request.get_json()

        if not all(key in data for key in ['name', 'price', 'totalAvailable']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        if Equipment.query.filter_by(name=data['name']).first():
            return jsonify({'success': False, 'message': 'Equipment name already exists'}), 400

        equipment = Equipment(
            name=data['name'],
            price=data['price'],
            total_available=data['totalAvailable']
        )

        db.session.add(equipment)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Equipment added successfully'})


@admin_bp.route('/api/equipment/<int:equipment_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def manage_equipment_item(equipment_id):
    """Update or delete equipment"""
    equipment = Equipment.query.get_or_404(equipment_id)

    if request.method == 'PUT':
        data = request.get_json()

        if 'name' in data and data['name'] != equipment.name:
            if Equipment.query.filter_by(name=data['name']).first():
                return jsonify({'success': False, 'message': 'Equipment name already exists'}), 400
            equipment.name = data['name']

        if 'price' in data:
            equipment.price = data['price']

        if 'totalAvailable' in data:
            equipment.total_available = data['totalAvailable']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Equipment updated successfully'})

    elif request.method == 'DELETE':
        # Check if equipment is in any bookings
        if BookingEquipment.query.filter_by(equipment_id=equipment_id).first():
            return jsonify({'success': False, 'message': 'Cannot delete equipment with existing bookings'}), 400

        db.session.delete(equipment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Equipment deleted successfully'})


@admin_bp.route('/api/coaches', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_coaches():
    """Get all coaches or add new coach"""
    if request.method == 'GET':
        coaches = Coach.query.order_by(Coach.name).all()

        # Get booking counts for each coach
        coaches_data = []
        for coach in coaches:
            total_bookings = Booking.query.filter_by(coach_id=coach.id).count()
            upcoming_bookings = Booking.query.filter(
                Booking.coach_id == coach.id,
                Booking.date >= date.today()
            ).count()

            coaches_data.append({
                'id': coach.id,
                'name': coach.name,
                'price': coach.price,
                'specialization': coach.specialization,
                'createdAt': coach.created_at.strftime('%Y-%m-%d'),
                'totalBookings': total_bookings,
                'upcomingBookings': upcoming_bookings
            })

        return jsonify(coaches_data)

    elif request.method == 'POST':
        data = request.get_json()

        if not all(key in data for key in ['name', 'price']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        if Coach.query.filter_by(name=data['name']).first():
            return jsonify({'success': False, 'message': 'Coach name already exists'}), 400

        coach = Coach(
            name=data['name'],
            price=data['price'],
            specialization=data.get('specialization', '')
        )

        db.session.add(coach)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Coach added successfully'})


@admin_bp.route('/api/coaches/<int:coach_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def manage_coach(coach_id):
    """Update or delete a coach"""
    coach = Coach.query.get_or_404(coach_id)

    if request.method == 'PUT':
        data = request.get_json()

        if 'name' in data and data['name'] != coach.name:
            if Coach.query.filter_by(name=data['name']).first():
                return jsonify({'success': False, 'message': 'Coach name already exists'}), 400
            coach.name = data['name']

        if 'price' in data:
            coach.price = data['price']

        if 'specialization' in data:
            coach.specialization = data['specialization']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Coach updated successfully'})

    elif request.method == 'DELETE':
        # Check if coach has bookings
        if Booking.query.filter_by(coach_id=coach_id).first():
            return jsonify({'success': False, 'message': 'Cannot delete coach with existing bookings'}), 400

        db.session.delete(coach)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Coach deleted successfully'})


@admin_bp.route('/api/pricing-rules', methods=['GET', 'PUT'])
@login_required
@admin_required
def manage_pricing_rules():
    """Get or update pricing rules"""
    if request.method == 'GET':
        rules = PricingRule.query.all()
        return jsonify([{
            'id': rule.id,
            'ruleType': rule.rule_type,
            'enabled': rule.enabled,
            'multiplier': rule.multiplier,
            'startTime': rule.start_time,
            'endTime': rule.end_time,
            'discount': rule.discount,
            'minItems': rule.min_items,
            'applyDays': rule.apply_days,
            'updatedAt': rule.updated_at.strftime('%Y-%m-%d %H:%M')
        } for rule in rules])

    elif request.method == 'PUT':
        data = request.get_json()

        if not data or 'rules' not in data:
            return jsonify({'success': False, 'message': 'No rules data provided'}), 400

        for rule_data in data['rules']:
            rule = PricingRule.query.filter_by(rule_type=rule_data['ruleType']).first()

            if rule:
                rule.enabled = rule_data.get('enabled', rule.enabled)
                rule.multiplier = rule_data.get('multiplier', rule.multiplier)
                rule.start_time = rule_data.get('startTime', rule.start_time)
                rule.end_time = rule_data.get('endTime', rule.end_time)
                rule.discount = rule_data.get('discount', rule.discount)
                rule.min_items = rule_data.get('minItems', rule.min_items)
                rule.apply_days = rule_data.get('applyDays', rule.apply_days)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Pricing rules updated successfully'})


@admin_bp.route('/api/reports/revenue')
@login_required
@admin_required
def get_revenue_report():
    """Get revenue reports"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Booking.query

    if start_date:
        query = query.filter(Booking.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Booking.date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    # Get total revenue
    total_revenue = db.session.query(db.func.sum(Booking.total_price)).scalar() or 0

    # Get revenue by court type
    revenue_by_court = db.session.query(
        Court.type,
        db.func.sum(Booking.total_price)
    ).join(Court).group_by(Court.type).all()

    # Get revenue by month
    revenue_by_month = db.session.query(
        db.func.strftime('%Y-%m', Booking.date),
        db.func.count(Booking.id),
        db.func.sum(Booking.total_price)
    ).group_by(db.func.strftime('%Y-%m', Booking.date)).order_by(
        db.func.strftime('%Y-%m', Booking.date).desc()
    ).limit(12).all()

    # Get top users by spending
    top_users = db.session.query(
        User.username,
        db.func.count(Booking.id).label('booking_count'),
        db.func.sum(Booking.total_price).label('total_spent')
    ).join(Booking).group_by(User.id).order_by(
        db.func.sum(Booking.total_price).desc()
    ).limit(10).all()

    return jsonify({
        'totalRevenue': total_revenue,
        'totalBookings': query.count(),
        'revenueByCourt': [
            {'type': court_type, 'revenue': revenue}
            for court_type, revenue in revenue_by_court
        ],
        'revenueByMonth': [
            {'month': month, 'bookings': count, 'revenue': revenue}
            for month, count, revenue in revenue_by_month
        ],
        'topUsers': [
            {'username': username, 'bookings': count, 'totalSpent': spent}
            for username, count, spent in top_users
        ]
    })


def get_currently_booked_quantity(equipment_id):
    """Helper function to get currently booked equipment quantity"""
    today = date.today()
    booked_bookings = Booking.query.filter(
        Booking.date >= today
    ).all()

    total_booked = 0
    for booking in booked_bookings:
        booking_eq = BookingEquipment.query.filter_by(
            booking_id=booking.id,
            equipment_id=equipment_id
        ).first()
        if booking_eq:
            total_booked += booking_eq.quantity

    return total_booked