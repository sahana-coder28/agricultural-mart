import os
from app import create_app
from extensions import db, bcrypt
from models import Admin

app = create_app()

with app.app_context():
    # Make sure all tables are created
    db.create_all()
    
    # Check if admin exists
    admin = Admin.query.filter_by(email="admin@agromart.com").first()
    if not admin:
        print("Creating default admin account (admin@agromart.com / password123)")
        hashed_password = bcrypt.generate_password_hash("password123").decode('utf-8')
        new_admin = Admin(username="SuperAdmin", email="admin@agromart.com", password_hash=hashed_password)
        db.session.add(new_admin)
        db.session.commit()
    else:
        print("Admin account already exists.")
