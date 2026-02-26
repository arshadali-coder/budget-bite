from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import MealPlan, Transaction
from datetime import date, timedelta
import random

meals_bp = Blueprint('meals', __name__, template_folder='templates')

# Meal database for suggestions
MEAL_DATABASE = {
    'Vegetarian': {
        'Breakfast': [
            {'name': 'Poha + Chai', 'cost': 30, 'calories': 280, 'protein': 8, 'score': 7.5, 'source': 'Mess'},
            {'name': 'Idli Sambar', 'cost': 35, 'calories': 300, 'protein': 10, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Upma + Coffee', 'cost': 25, 'calories': 250, 'protein': 6, 'score': 7.0, 'source': 'Mess'},
            {'name': 'Bread Butter + Milk', 'cost': 20, 'calories': 320, 'protein': 9, 'score': 6.5, 'source': 'Self'},
            {'name': 'Paratha + Curd', 'cost': 40, 'calories': 380, 'protein': 11, 'score': 7.5, 'source': 'Canteen'},
            {'name': 'Oats + Banana', 'cost': 15, 'calories': 230, 'protein': 7, 'score': 8.5, 'source': 'Self'},
        ],
        'Lunch': [
            {'name': 'Dal Rice + Sabzi + Roti', 'cost': 60, 'calories': 550, 'protein': 18, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Rajma Chawal', 'cost': 50, 'calories': 520, 'protein': 20, 'score': 8.5, 'source': 'Mess'},
            {'name': 'Chole Bhature', 'cost': 55, 'calories': 600, 'protein': 16, 'score': 6.5, 'source': 'Canteen'},
            {'name': 'Thali (Full)', 'cost': 70, 'calories': 650, 'protein': 22, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Veg Biryani', 'cost': 65, 'calories': 480, 'protein': 12, 'score': 7.0, 'source': 'Canteen'},
        ],
        'Dinner': [
            {'name': 'Roti + Paneer + Dal', 'cost': 70, 'calories': 480, 'protein': 20, 'score': 8.5, 'source': 'Mess'},
            {'name': 'Dal Khichdi', 'cost': 40, 'calories': 400, 'protein': 14, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Roti + Mix Veg', 'cost': 55, 'calories': 420, 'protein': 12, 'score': 7.5, 'source': 'Mess'},
            {'name': 'Pav Bhaji', 'cost': 50, 'calories': 450, 'protein': 10, 'score': 7.0, 'source': 'Canteen'},
        ],
        'Snack': [
            {'name': 'Banana + Biscuits', 'cost': 25, 'calories': 180, 'protein': 3, 'score': 6.0, 'source': 'Self'},
            {'name': 'Samosa + Chai', 'cost': 20, 'calories': 250, 'protein': 4, 'score': 5.0, 'source': 'Canteen'},
            {'name': 'Fruit Chaat', 'cost': 30, 'calories': 120, 'protein': 2, 'score': 8.5, 'source': 'Self'},
            {'name': 'Peanut Chikki', 'cost': 15, 'calories': 200, 'protein': 7, 'score': 7.0, 'source': 'Self'},
            {'name': 'Sprout Salad', 'cost': 20, 'calories': 150, 'protein': 9, 'score': 9.0, 'source': 'Self'},
        ]
    },
    'Non-Vegetarian': {
        'Breakfast': [
            {'name': 'Egg Bhurji + Toast', 'cost': 35, 'calories': 350, 'protein': 18, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Omelette + Bread', 'cost': 30, 'calories': 320, 'protein': 16, 'score': 7.5, 'source': 'Mess'},
            {'name': 'Boiled Eggs + Chai', 'cost': 25, 'calories': 250, 'protein': 14, 'score': 8.5, 'source': 'Self'},
        ],
        'Lunch': [
            {'name': 'Chicken Curry + Rice', 'cost': 80, 'calories': 600, 'protein': 30, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Egg Fried Rice', 'cost': 60, 'calories': 500, 'protein': 18, 'score': 7.0, 'source': 'Canteen'},
            {'name': 'Fish Curry + Rice', 'cost': 90, 'calories': 550, 'protein': 28, 'score': 8.5, 'source': 'Mess'},
        ],
        'Dinner': [
            {'name': 'Chicken Biryani', 'cost': 100, 'calories': 650, 'protein': 32, 'score': 7.5, 'source': 'Canteen'},
            {'name': 'Egg Curry + Roti', 'cost': 55, 'calories': 420, 'protein': 18, 'score': 8.0, 'source': 'Mess'},
            {'name': 'Chicken + Dal + Roti', 'cost': 85, 'calories': 550, 'protein': 28, 'score': 8.5, 'source': 'Mess'},
        ],
        'Snack': [
            {'name': 'Egg Roll', 'cost': 40, 'calories': 300, 'protein': 14, 'score': 6.5, 'source': 'Canteen'},
            {'name': 'Chicken Sandwich', 'cost': 50, 'calories': 350, 'protein': 18, 'score': 7.0, 'source': 'Canteen'},
        ]
    }
}


@meals_bp.route('/')
@login_required
def index():
    today = date.today()
    today_meals = MealPlan.query.filter_by(user_id=current_user.id, date=today)\
        .order_by(MealPlan.meal_type).all()

    total_cost = sum(m.cost for m in today_meals)
    total_calories = sum(m.calories for m in today_meals)
    total_protein = sum(m.protein for m in today_meals)

    # Get suggestion based on remaining budget
    daily_limit = current_user.get_daily_limit()
    today_spent = current_user.get_today_spent()
    food_budget_left = max(0, daily_limit * 0.6 - sum(m.cost for m in today_meals if m.is_completed))

    # Weekly meal plan
    week_meals = {}
    for i in range(7):
        d = today + timedelta(days=i)
        day_meals = MealPlan.query.filter_by(user_id=current_user.id, date=d).all()
        week_meals[d.strftime('%A')] = {'date': d, 'meals': day_meals, 'total': sum(m.cost for m in day_meals)}

    # Cost comparison
    pref = current_user.food_preference or 'Vegetarian'
    meals_data = MEAL_DATABASE.get(pref, MEAL_DATABASE['Vegetarian'])
    mess_avg = sum(m['cost'] for meals in meals_data.values() for m in meals if m['source'] == 'Mess') / max(1, sum(1 for meals in meals_data.values() for m in meals if m['source'] == 'Mess'))
    canteen_avg = sum(m['cost'] for meals in meals_data.values() for m in meals if m['source'] == 'Canteen') / max(1, sum(1 for meals in meals_data.values() for m in meals if m['source'] == 'Canteen'))

    # Smart suggestion
    if food_budget_left < 50:
        suggestion = "Budget tight! Try mess meals or cook something simple today 🍳"
    elif food_budget_left < 100:
        suggestion = "Today's cheapest protein option: Sprout Salad (₹20) or Dal Rice (₹60) 💪"
    else:
        suggestion = "Good budget! You can afford a balanced mess meal today 🎉"

    return render_template('meals/index.html',
        today_meals=today_meals,
        total_cost=total_cost,
        total_calories=total_calories,
        total_protein=total_protein,
        food_budget_left=food_budget_left,
        week_meals=week_meals,
        mess_avg=mess_avg,
        canteen_avg=canteen_avg,
        suggestion=suggestion,
    )


@meals_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        meal = MealPlan(
            user_id=current_user.id,
            date=date.fromisoformat(request.form.get('date', date.today().isoformat())),
            meal_type=request.form.get('meal_type', 'Lunch'),
            name=request.form.get('name', ''),
            cost=float(request.form.get('cost', 0)),
            calories=int(request.form.get('calories', 0)),
            protein=float(request.form.get('protein', 0)),
            source=request.form.get('source', 'Mess'),
            nutrition_score=float(request.form.get('nutrition_score', 7))
        )
        db.session.add(meal)
        db.session.commit()
        flash(f'Meal planned: {meal.name} 🍽️', 'success')
        return redirect(url_for('meals.index'))
    return render_template('meals/add.html', today=date.today().isoformat())


@meals_bp.route('/auto-plan', methods=['POST'])
@login_required
def auto_plan():
    """Auto-generate meal plan for the week."""
    pref = current_user.food_preference or 'Vegetarian'
    meals_data = MEAL_DATABASE.get(pref, MEAL_DATABASE['Vegetarian'])
    daily_limit = current_user.get_daily_limit()
    food_budget = daily_limit * 0.6

    today = date.today()
    for i in range(7):
        d = today + timedelta(days=i)
        existing = MealPlan.query.filter_by(user_id=current_user.id, date=d).first()
        if existing:
            continue

        for meal_type in ['Breakfast', 'Lunch', 'Snack', 'Dinner']:
            options = meals_data.get(meal_type, [])
            affordable = [m for m in options if m['cost'] <= food_budget * 0.35]
            if not affordable:
                affordable = options
            if affordable:
                choice = random.choice(affordable)
                meal = MealPlan(
                    user_id=current_user.id, date=d, meal_type=meal_type,
                    name=choice['name'], cost=choice['cost'], calories=choice['calories'],
                    protein=choice['protein'], nutrition_score=choice['score'], source=choice['source']
                )
                db.session.add(meal)

    db.session.commit()
    flash('Weekly meal plan generated! 🗓️', 'success')
    return redirect(url_for('meals.index'))


@meals_bp.route('/complete/<int:meal_id>', methods=['POST'])
@login_required
def complete(meal_id):
    meal = MealPlan.query.filter_by(id=meal_id, user_id=current_user.id).first_or_404()
    meal.is_completed = True

    # Auto-log as expense
    txn = Transaction(
        user_id=current_user.id,
        amount=meal.cost,
        category='Food',
        subcategory=meal.source,
        description=meal.name,
        is_food=True,
        meal_type=meal.meal_type
    )
    db.session.add(txn)
    db.session.commit()
    flash(f'{meal.name} completed & logged as ₹{meal.cost:.0f} expense! ✅', 'success')
    return redirect(url_for('meals.index'))


@meals_bp.route('/suggestions')
@login_required
def suggestions():
    pref = current_user.food_preference or 'Vegetarian'
    meals_data = MEAL_DATABASE.get(pref, MEAL_DATABASE['Vegetarian'])
    daily_limit = current_user.get_daily_limit()

    return jsonify({
        'suggestions': meals_data,
        'daily_food_budget': daily_limit * 0.6,
        'preference': pref
    })


@meals_bp.route('/delete/<int:meal_id>', methods=['POST'])
@login_required
def delete(meal_id):
    meal = MealPlan.query.filter_by(id=meal_id, user_id=current_user.id).first_or_404()
    db.session.delete(meal)
    db.session.commit()
    flash('Meal removed! 🗑️', 'info')
    return redirect(url_for('meals.index'))
