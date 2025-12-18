🏸 Sports Court Booking Platform

A Flask-based court booking system that supports multi-resource bookings, dynamic pricing, and admin configuration for courts, equipment, coaches, and pricing rules.

🚀 Features
	•	Book court + optional equipment + optional coach in a single transaction
	•	Atomic booking (all resources reserved or none)
	•	Dynamic pricing based on:
	•	Peak hours
	•	Weekends
	•	Indoor courts
	•	Optional equipment & coach
	•	Admin-configurable resources and pricing rules
	•	Slot availability view by date

🛠 Tech Stack
	•	Backend: Flask, SQLAlchemy
	•	Database: SQLite
	•	Frontend: HTML, CSS, JavaScript, Bootstrap
	•	Authentication: Flask-Login

⚙️ Setup Instructions

# Clone repository
git clone <repo-url>
cd court-booking

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

## Setup Instructions

# Initialize database and seed data
python init.py

# Start application
python app.py

App will run at:
👉 http://127.0.0.1:5000

📦 Seed Data
The application auto-loads seed data for:
	•	Courts (indoor & outdoor)
	•	Equipment inventory
	•	Coaches and availability
	•	Pricing rules

This ensures the app is usable immediately after setup.

📌 Assumptions Made
	•	Time slots are booked in 1-hour intervals
	•	Only one coach can be assigned per booking
	•	Equipment quantity is limited and tracked
	•	Pricing rules are stackable
	•	Admin configuration is done via backend routes (no separate admin UI)

📦 Seed Data

The application automatically loads the following seed data on first run.

Courts
	•	Court 1 – Indoor Badminton
	•	Court 2 – Indoor Badminton
	•	Court 3 – Outdoor Badminton
	•	Court 4 – Outdoor Badminton

Equipment
	•	Badminton Rackets – Quantity: 10
	•	Sports Shoes – Quantity: 6

Coaches
	•	Coach A – Morning availability
	•	Coach B – Evening availability
	•	Coach C – Weekend availability

Pricing Rules
	•	Peak Hours (6 PM – 9 PM): +20%
	•	Weekend Surcharge: +15%
	•	Indoor Court Premium: +25%
	•	Coach Fee: Fixed hourly rate
	•	Equipment Fee: Per item per booking

All pricing rules are configurable and stackable.

📌 Assumptions
	•	Bookings are made in 1-hour time slots
	•	One coach can be selected per booking
	•	Equipment inventory is limited and tracked
	•	Pricing rules can stack (e.g., indoor + peak + weekend)
	•	Admin actions are handled via backend routes


🗄 Database Design & Pricing Engine (Design Explanation)

The database is designed using a normalized relational structure to ensure flexibility, data integrity, and scalability. Core entities such as Courts, Equipment, and Coaches are modeled independently so that their availability and pricing can be managed separately.

A central Booking table represents a single reservation transaction. This table links to users, courts, time slots, and optional resources. Equipment usage is managed using a junction table that records which equipment items are assigned to a booking and in what quantity. This ensures accurate inventory tracking and prevents overbooking.

The system enforces atomic booking. Before a booking is confirmed, the availability of the selected court, equipment, and coach is validated. If any resource is unavailable, the transaction is rolled back, ensuring that partial bookings never occur.

The pricing engine follows a rule-driven approach. Instead of hardcoding pricing logic, all modifiers are stored in a PricingRule table. Each rule defines a condition (such as peak hours, weekends, or indoor courts) and a pricing impact (percentage-based or fixed amount). During booking, the base court price is calculated first, after which all active and applicable pricing rules are evaluated and applied.

Pricing rules are stackable, allowing multiple conditions to affect the final price. Optional resources such as coaches and equipment are added as independent cost components. This design makes the system highly extensible — new pricing rules (e.g., holiday surcharges) can be added without changing application code.

Overall, the architecture prioritizes clarity, maintainability, and real-world booking constraints, making it suitable for scalable sports facility management.