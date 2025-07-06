from datetime import datetime, timedelta
from operator import or_
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
import openai
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from database import db 
from models import User, Recipe, Favourite, ShoppingList, MealPlan
from openai import * # type: ignore
from openai import OpenAI  # Import the OpenAI client
from flask_wtf.csrf import CSRFProtect 

# Define Blueprint
routes = Blueprint("routes", __name__)
csrf = CSRFProtect()

# Set OpenAI API Key
client = OpenAI(api_key="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")

@routes.route("/search_recipes", methods=["GET"])
def search_recipes():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        # Use SQLAlchemy session directly
        recipes = db.session.query(Recipe).filter(
            Recipe.name.ilike(f'%{query}%')
        ).limit(10).all()
        
        recipes_data = [{
            "id": recipe.id,
            "name": recipe.name,
            "minutes": recipe.minutes
        } for recipe in recipes]
        
        return jsonify(recipes_data)
        
    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}")
        return jsonify([])

@routes.route("/move_meal", methods=["POST"])
@login_required
def move_meal():
    try:
        data = request.get_json()
        meal_plan_id = data.get("meal_plan_id")
        new_day = data.get("new_day")

        if not meal_plan_id or not new_day:
            return jsonify({"error": "Missing required fields"}), 400

        meal_plan = db.session.query(MealPlan).get(meal_plan_id)
        if not meal_plan or meal_plan.user_id != current_user.id:
            return jsonify({"error": "Meal plan not found"}), 404

        # Check if new day already has 5 meals
        meal_count = db.session.query(MealPlan).filter(
            MealPlan.user_id == current_user.id,
            MealPlan.day == new_day
        ).count()
        
        if meal_count >= 5:
            return jsonify({"error": "Maximum 5 meals per day"}), 400

        meal_plan.day = new_day
        db.session.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Move meal error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@routes.route("/add_meal", methods=["POST"])
@login_required
def add_meal():
    try:
        data = request.get_json()
        day = data.get("day")
        recipe_id = data.get("recipe_id")

        if not day or not recipe_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Check if recipe exists
        recipe = db.session.query(Recipe).get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404

        # Check if day already has 5 meals
        meal_count = db.session.query(MealPlan).filter(
            MealPlan.user_id == current_user.id,
            MealPlan.day == day
        ).count()
        
        if meal_count >= 5:
            return jsonify({"error": "Maximum 5 meals per day"}), 400

        # Check if recipe already added for this day
        existing = db.session.query(MealPlan).filter(
            MealPlan.user_id == current_user.id,
            MealPlan.day == day,
            MealPlan.recipe_id == recipe_id
        ).first()
        
        if existing:
            return jsonify({"error": "Recipe already added for this day"}), 400

        new_plan = MealPlan(
            user_id=current_user.id,
            recipe_id=recipe_id,
            day=day
        )
        db.session.add(new_plan)
        db.session.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add meal error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@routes.route("/remove_meal/<int:meal_plan_id>", methods=["POST"])
@login_required
def remove_meal(meal_plan_id):
    try:
        meal_plan = db.session.query(MealPlan).get(meal_plan_id)
        if not meal_plan or meal_plan.user_id != current_user.id:
            return jsonify({"error": "Meal plan not found"}), 404
            
        db.session.delete(meal_plan)
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Remove meal error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@routes.route("/meal_planner", methods=["GET"])
@login_required
def meal_planner():
    try:
        meal_plans = db.session.query(MealPlan).filter(
            MealPlan.user_id == current_user.id
        ).order_by(MealPlan.day).all()
        
        recipes = db.session.query(Recipe).limit(50).all()  # For dropdown if needed
        
        return render_template("meal_planner.html", 
                             meal_plans=meal_plans,
                             recipes=recipes)
                             
    except Exception as e:
        current_app.logger.error(f"Meal planner error: {str(e)}")
        flash("Error loading meal planner", "error")
        return render_template("meal_planner.html", 
                             meal_plans=[],
                             recipes=[])
    
    
@routes.route("/remove_meal_by_day/<string:day>", methods=["POST"])
@login_required
def remove_meal_by_day(day):
    meal_plan = MealPlan.query.filter_by(user_id=current_user.id, day=day).first()
    if meal_plan:
        db.session.delete(meal_plan)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Meal plan not found"})

@routes.route("/add_to_shopping_list", methods=["POST"])
@login_required
def add_to_shopping_list():
    try:
        data = request.get_json()
        ingredient = data.get("ingredient", "").strip()
        
        if not ingredient:
            return jsonify({"error": "Ingredient cannot be empty"}), 400

        # Check if ingredient already exists in user's shopping list
        existing = ShoppingList.query.filter_by(
            user_id=current_user.id,
            ingredient=ingredient
        ).first()
        
        if existing:
            return jsonify({"success": True, "message": "Ingredient already in list"})

        new_item = ShoppingList(
            user_id=current_user.id,
            ingredient=ingredient,
            category=data.get("category", "uncategorized")
        )
        db.session.add(new_item)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Ingredient added"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@routes.route("/add_ingredient_manually", methods=["POST"])
@login_required
def add_ingredient_manually():
    try:
        ingredient = request.form.get("ingredient").strip()
        category = request.form.get("category", "other")
        
        if not ingredient:
            flash("Ingredient cannot be empty", "danger")
            return redirect(url_for("routes.shopping_list"))

        new_item = ShoppingList(
            user_id=current_user.id,
            ingredient=ingredient,
            category=category
        )
        db.session.add(new_item)
        db.session.commit()
        
        flash("Ingredient added to shopping list!", "success")
        return redirect(url_for("routes.shopping_list"))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding ingredient: {str(e)}")
        flash("Error adding ingredient", "danger")
        return redirect(url_for("routes.shopping_list"))


@routes.route("/shopping_list")
@login_required
def shopping_list():
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(ShoppingList.category).all()
    return render_template("shopping_list.html", items=items)

@routes.route("/toggle_shopping_item/<int:item_id>", methods=["POST"])
@login_required
def toggle_shopping_item(item_id):
    try:
        item = ShoppingList.query.get_or_404(item_id)
        if item.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        item.checked = not item.checked
        db.session.commit()
        return jsonify({"success": True, "checked": item.checked})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling item: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@routes.route("/remove_shopping_item/<int:item_id>", methods=["POST"])
@login_required
def remove_shopping_item(item_id):
    try:
        item = ShoppingList.query.get_or_404(item_id)
        if item.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing item: {str(e)}")
        return jsonify({"error": "Server error"}), 500


@routes.route("/update_category/<int:item_id>", methods=["POST"])
@login_required
def update_shopping_list_category(item_id):
    try:
        item = ShoppingList.query.get_or_404(item_id)
        if item.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()
        new_category = data.get("category", "other")
        
        if new_category not in ["produce", "dairy", "spices", "meat", "grains", "other"]:
            return jsonify({"error": "Invalid category"}), 400

        item.category = new_category
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating category: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@routes.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = User.query.get(current_user.id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("routes.home"))

    if request.method == "POST":
        # Update user details
        user.username = request.form.get("username", user.username)
        user.email = request.form.get("email", user.email)
        
        # Update password if provided
        new_password = request.form.get("new_password")
        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("routes.profile"))

    return render_template("edit_profile.html", user=user)

@routes.route("/profile")
@login_required
def profile():
    # Fetch the current user's details from the database
    user = User.query.get(current_user.id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("routes.home"))
    
    return render_template("profile.html", user=user)

@routes.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    max_time = request.args.get("max_time", type=int)
    include_ingredients = request.args.get("include_ingredients", "").split(",")
    exclude_ingredients = request.args.get("exclude_ingredients", "").split(",")
    dietary_requirements = request.args.get("dietary_requirements", "").split(",")

    # Base query
    recipes_query = Recipe.query

    # Apply filters
    if query:
        recipes_query = recipes_query.filter(Recipe.name.ilike(f'%{query}%'))
    if max_time:
        recipes_query = recipes_query.filter(Recipe.minutes <= max_time)
    if include_ingredients:
        for ingredient in include_ingredients:
            if ingredient:
                recipes_query = recipes_query.filter(Recipe.ingredients.ilike(f'%{ingredient}%'))
    if exclude_ingredients:
        for ingredient in exclude_ingredients:
            if ingredient:
                recipes_query = recipes_query.filter(~Recipe.ingredients.ilike(f'%{ingredient}%'))
    if dietary_requirements:
        for requirement in dietary_requirements:
            if requirement:
                recipes_query = recipes_query.filter(Recipe.tags.ilike(f'%{requirement}%'))

    # Execute the query
    recipes = recipes_query.all()

    # Fetch the current user's favorite recipe IDs
    if current_user.is_authenticated:
        user_favorites = {fav.recipe_id for fav in Favourite.query.filter_by(user_id=current_user.id).all()}
    else:
        user_favorites = set()

    # Add 'favorited' attribute to each recipe
    for recipe in recipes:
        recipe.favorited = recipe.id in user_favorites

    return render_template("search_results.html", recipes=recipes, query=query, max_time=max_time,
                          include_ingredients=include_ingredients, exclude_ingredients=exclude_ingredients,
                          dietary_requirements=dietary_requirements)


@routes.route("/chatbot", methods=["POST"])
def chatbot():
    user_message = request.json.get("message")
    
    # Check if the message is empty
    if not user_message or not user_message.strip():
        return jsonify({"error": "Message cannot be empty"}), 400
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a food expert who provides recipes, cooking tips, and nutritional advice. You can suggest recipes based on available ingredients, give cooking techniques, and provide alternative ingredient substitutions. Politely refuse to answer non-food-related questions."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response["choices"][0]["message"]["content"]
        return jsonify({"reply": bot_reply})
    
    except openai.AuthenticationError:
        return jsonify({"error": "Invalid OpenAI API key"}), 401
    except openai.RateLimitError:
        return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
    except openai.APIError as e:
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Hash password function
def hash_password(password):
    return generate_password_hash(password)

# Function to get recipes from SQLite
def get_recipes(query=None):
    conn = sqlite3.connect("databases/recipes.db")
    cursor = conn.cursor()
    if query:
        cursor.execute("SELECT id, name, minutes FROM recipes WHERE name LIKE ?", ('%' + query + '%',))
    else:
        cursor.execute("SELECT id, name, minutes FROM recipes LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "minutes": row[2]} for row in rows]

@routes.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("routes.home"))
    return render_template("login.html")

@routes.route("/home")
@login_required
def home():
    try:
        # Basic recipe query
        recipes = Recipe.query.limit(10).all()
        
        # Get user favorites
        user_favorites = {fav.recipe_id for fav in 
                         db.session.query(Favourite.recipe_id)
                         .filter(Favourite.user_id == current_user.id)
                         .all()}
        
        # Simple recommendation - just random recipes not in favorites
        recommended = Recipe.query.filter(
            ~Recipe.id.in_(user_favorites)
        ).order_by(db.func.random()).limit(5).all()
        
        # Add recommendation reason
        for recipe in recommended:
            recipe.recommendation_reason = "Recommended for you"
        
        return render_template(
            "home.html",
            recipes=recipes,
            favourite_recipe_ids=user_favorites,
            recommended_recipes=recommended
        )
    except Exception as e:
        print(f"Error in home route: {e}")
        # Fallback if anything fails
        return render_template(
            "home.html",
            recipes=[],
            favourite_recipe_ids=set(),
            recommended_recipes=[]
        )
@routes.route("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return render_template("recipe_detail.html", recipe=recipe)

@routes.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("routes.home"))
        
    if request.method == "POST":
        email = request.form.get("email", "").lower()
        password = request.form.get("password", "")
        
        # Validate form fields
        if not email or not password:
            flash("Please fill in all fields", "danger")
            return redirect(url_for("routes.login"))
            
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for("routes.home"))
            
        flash("Invalid email or password", "danger")
    
    # For GET requests or failed POST requests
    return render_template("login.html", 
                         next=request.args.get('next'))

@routes.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"].lower()
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already exists. Please login.", "danger")
            return redirect(url_for("routes.login"))
        new_user = User(username=username, email=email, password=hash_password(password))
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("routes.login"))
    return render_template("signup.html")

@routes.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("routes.index"))



@routes.route("/add_favourite/<int:recipe_id>", methods=["POST"])
@login_required
def add_favourite(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if not Favourite.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first():
        db.session.add(Favourite(user_id=current_user.id, username=current_user.username, recipe_id=recipe.id, recipe_name=recipe.name))
        db.session.commit()
        flash("Recipe added to favourites!", "success")
    else:
        flash("Recipe is already in your favourites.", "info")
    return redirect(url_for("routes.recipe_detail", recipe_id=recipe_id))



@routes.route("/remove_favourite/<int:recipe_id>", methods=["POST"])
@login_required
@csrf.exempt  # Temporary exemption for testing - remove in production
def remove_favourite(recipe_id):
    try:
        fav = Favourite.query.filter_by(
            user_id=current_user.id,
            recipe_id=recipe_id
        ).first()
        
        if not fav:
            return jsonify({
                "success": False,
                "error": "Recipe not found in your favourites"
            }), 404
            
        db.session.delete(fav)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Recipe removed from favourites"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error removing favourite: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Server error while removing favourite"
        }), 500
    
@routes.route("/toggle_favourite/<int:recipe_id>", methods=["POST"])
@login_required
def toggle_favourite(recipe_id):
    try:
        fav = Favourite.query.filter_by(
            user_id=current_user.id, 
            recipe_id=recipe_id
        ).first()
        
        if fav:
            db.session.delete(fav)
            status = "removed"
        else:
            new_fav = Favourite(
                user_id=current_user.id,
                recipe_id=recipe_id,
                recipe_name=Recipe.query.get(recipe_id).name
            )
            db.session.add(new_fav)
            status = "added"
        
        db.session.commit()
        return jsonify({"status": status})
    except Exception as e:
        print(f"Error toggling favorite: {e}")
        return jsonify({"error": "Server error"}), 500

@routes.route("/favourites")
@login_required
def favourites():
    try:
        fav_recipes = db.session.query(Recipe)\
            .join(Favourite, Recipe.id == Favourite.recipe_id)\
            .filter(Favourite.user_id == current_user.id)\
            .all()
            
        return render_template("favourites.html", recipes=fav_recipes)
        
    except Exception as e:
        current_app.logger.error(f"Error loading favourites: {str(e)}")
        flash("Error loading your favourites", "error")
        return render_template("favourites.html", recipes=[])