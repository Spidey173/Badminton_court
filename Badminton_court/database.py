# database.py
from models import db, User, Court, Equipment, Coach, PricingRule


def init_db():
    db.create_all()


def seed_data():
    # Only seed if tables are empty
    if Court.query.count() == 0:
        # Seed courts
        courts = [
            Court(name='Court 1 - Indoor', type='indoor', base_price=600, is_active=True),
            Court(name='Court 2 - Indoor', type='indoor', base_price=600, is_active=True),
            Court(name='Court 3 - Outdoor', type='outdoor', base_price=400, is_active=True),
            Court(name='Court 4 - Outdoor', type='outdoor', base_price=400, is_active=True)
        ]

        # Seed equipment
        equipment = [
            Equipment(name='Badminton Racket', price=50, total_available=10),
            Equipment(name='Shuttlecocks (tube)', price=30, total_available=20),
            Equipment(name='Sports Shoes', price=100, total_available=8),
            Equipment(name='Sports Kit', price=150, total_available=5)
        ]

        # Seed coaches
        coaches = [
            Coach(name='Coach Rajesh', price=500, specialization='Advanced Training'),
            Coach(name='Coach Priya', price=500, specialization='Beginners'),
            Coach(name='Coach Amit', price=500, specialization='Tournament Prep')
        ]

        # Seed pricing rules
        pricing_rules = [
            PricingRule(rule_type='peak_hours', enabled=True, multiplier=1.5,
                       start_time='18:00', end_time='21:00', apply_days='1,2,3,4,5'),
            PricingRule(rule_type='weekend', enabled=True, multiplier=1.3),
            PricingRule(rule_type='indoor', enabled=True, multiplier=1.2),
            PricingRule(rule_type='multiple_hours', enabled=True, discount=0.1),
            PricingRule(rule_type='bundle', enabled=True, discount=0.15, min_items=3)
        ]

        # Add to database
        for court in courts:
            db.session.add(court)

        for eq in equipment:
            db.session.add(eq)

        for coach in coaches:
            db.session.add(coach)

        for rule in pricing_rules:
            db.session.add(rule)

        db.session.commit()
        print("Database seeded with initial data!")