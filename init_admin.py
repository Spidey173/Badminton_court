# init_admin.py - UPDATED
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import after setting up the path
from app import app, db
from database import init_db, seed_data

with app.app_context():
    # Initialize database
    init_db()

    # Seed initial data
    seed_data()

    print("Database initialized and seeded successfully!")
    print("First user to register will be the admin.")