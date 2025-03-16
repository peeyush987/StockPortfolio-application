from app import app, db

# Create all tables inside the application context
with app.app_context():
    db.create_all()
    print("Database tables created!")
