import sqlite3
from flask_migrate import Migrate
import pandas as pd
from flask_wtf.csrf import CSRFProtect

# Connect to SQLite database (creates a file if it doesn't exist)
conn = sqlite3.connect("recipes.db")
cursor = conn.cursor()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from database import db  # Import db after defining it in database.py
from routes import routes  # Import routes

# Initialize Flask app
app = Flask(__name__)
migrate = Migrate(app, db)  # Make sure Migrate is initialized here
csrf = CSRFProtect(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\Admin\Desktop\college\major\databases\recipes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

app.config.update(
    SECRET_KEY='your-very-secret-key-change-this',
    WTF_CSRF_SECRET_KEY='a-different-secret-key',
    WTF_CSRF_TIME_LIMIT=3600
)
# Initialize Database
db.init_app(app)
# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

 

from models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# Import routes
from routes import *
app.register_blueprint(routes)


if __name__ == "__main__":
    app.run(debug=True)

