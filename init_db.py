from app import app, db

'''with app.app_context():
    db.create_all()
    print("Database tables created successfully!")'''
from flask_migrate import Migrate

# After creating your app and db objects
migrate = Migrate(app, db)
