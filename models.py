from datetime import datetime
from database import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    # Relationships
    favourites = db.relationship('Favourite', back_populates='user')
    shopping_items = db.relationship('ShoppingList', back_populates='user')
    meal_plans = db.relationship('MealPlan', back_populates='user')
    search_history = db.relationship('SearchHistory', back_populates='user')

class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    submitted = db.Column(db.String, nullable=False)
    tags = db.Column(db.Text, nullable=True)
    n_steps = db.Column(db.Integer, nullable=True)
    steps = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    ingredients = db.Column(db.Text, nullable=True)
    n_ingredients = db.Column(db.Integer, nullable=True)
    calories = db.Column(db.Float, nullable=True)
    total_fat = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    sodium = db.Column(db.Float, nullable=True)
    protein = db.Column(db.Float, nullable=True)
    saturated_fat = db.Column(db.Float, nullable=True)
    carbohydrates = db.Column(db.Float, nullable=True)
    
    # Relationships
    favourites = db.relationship('Favourite', back_populates='recipe')
    meal_plans = db.relationship('MealPlan', back_populates='recipe')

class Favourite(db.Model):
    __tablename__ = 'favourite'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False, default='')
    recipe_name = db.Column(db.String(255), nullable=False, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='favourites')
    recipe = db.relationship('Recipe', back_populates='favourites')

class ShoppingList(db.Model):
    __tablename__ = 'shopping_list'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ingredient = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    checked = db.Column(db.Boolean, nullable=True)
    
    # Relationships
    user = db.relationship('User', back_populates='shopping_items')

class MealPlan(db.Model):
    __tablename__ = 'meal_plan'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='meal_plans')
    recipe = db.relationship('Recipe', back_populates='meal_plans')

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    query = db.Column(db.String(255))
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='search_history')