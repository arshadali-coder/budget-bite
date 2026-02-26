import os
from flask import Flask
from app.config import Config
from app.extensions import db, login_manager, migrate


def create_app(config_class=Config):
    # Resolve absolute paths so templates/static work on Vercel (/var/task)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.expenses.routes import expenses_bp
    from app.blueprints.budget.routes import budget_bp
    from app.blueprints.meals.routes import meals_bp
    from app.blueprints.analytics.routes import analytics_bp
    from app.blueprints.alerts.routes import alerts_bp
    from app.blueprints.social.routes import social_bp
    from app.blueprints.gamification.routes import gamification_bp
    from app.blueprints.dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(expenses_bp, url_prefix='/expenses')
    app.register_blueprint(budget_bp, url_prefix='/budget')
    app.register_blueprint(meals_bp, url_prefix='/meals')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(alerts_bp, url_prefix='/alerts')
    app.register_blueprint(social_bp, url_prefix='/social')
    app.register_blueprint(gamification_bp, url_prefix='/gamification')

    # Root redirect
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.home'))
        return redirect(url_for('auth.login'))

    # Create tables
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _seed_demo_data(app)

    # Template context
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        unread_count = 0
        if current_user.is_authenticated:
            from app.models import Alert
            unread_count = Alert.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {
            'currency': app.config.get('DEFAULT_CURRENCY', '₹'),
            'categories': app.config.get('CATEGORIES', []),
            'food_subcategories': app.config.get('FOOD_SUBCATEGORIES', []),
            'unread_alerts': unread_count
        }

    return app


def _seed_demo_data(app):
    """Seed demo data for the demo user if it doesn't exist."""
    from app.models import User, Transaction, Budget, MealPlan, Badge, Alert, SavingsGoal
    from datetime import datetime, date, timedelta
    import random

    demo_user = User.query.filter_by(email='demo@budgetbite.app').first()
    if demo_user:
        return

    # Create demo user
    demo_user = User(
        name='Alex Student',
        email='demo@budgetbite.app',
        monthly_budget=8000.0,
        living_type='Hostel',
        food_preference='Vegetarian',
        onboarding_complete=True,
        avatar=''
    )
    db.session.add(demo_user)
    db.session.flush()

    # Create budget
    today = date.today()
    budget = Budget(
        user_id=demo_user.id,
        month=today.month,
        year=today.year,
        total_amount=8000.0,
        food_allocation=4000.0,
        travel_allocation=1500.0,
        academic_allocation=1000.0,
        entertainment_allocation=1000.0,
        emergency_reserve=500.0
    )
    budget.categories = {
        'Food': 4000, 'Travel': 1500, 'Academic': 1000,
        'Entertainment': 1000, 'Shopping': 0, 'Health': 0, 'Misc': 500
    }
    db.session.add(budget)

    # Create transactions for the past 20 days
    categories_data = [
        ('Food', True, ['Mess lunch', 'Canteen snack', 'Tea and biscuits', 'Dinner at mess', 'Juice', 'Maggi', 'Samosa', 'Fruit salad']),
        ('Travel', False, ['Auto to college', 'Bus ticket', 'Metro card recharge', 'Rickshaw']),
        ('Academic', False, ['Xerox notes', 'Pen and notebook', 'Lab printout', 'Book from library']),
        ('Entertainment', False, ['Movie ticket', 'Netflix share', 'Game recharge']),
        ('Misc', False, ['Laundry', 'Phone recharge', 'Haircut']),
    ]

    for day_offset in range(20, 0, -1):
        txn_date = datetime.now() - timedelta(days=day_offset)
        num_transactions = random.randint(2, 5)
        for _ in range(num_transactions):
            cat_data = random.choice(categories_data)
            category, is_food, descriptions = cat_data
            amount = random.randint(10, 250) if is_food else random.randint(20, 400)
            txn = Transaction(
                user_id=demo_user.id,
                amount=amount,
                category=category,
                description=random.choice(descriptions),
                date=txn_date,
                is_food=is_food,
                meal_type=random.choice(['Breakfast', 'Lunch', 'Dinner', 'Snack']) if is_food else None
            )
            db.session.add(txn)

    # Add today's transactions
    for desc, amount, cat in [('Mess breakfast', 50, 'Food'), ('Auto to class', 30, 'Travel'), ('Canteen coffee', 20, 'Food')]:
        txn = Transaction(
            user_id=demo_user.id, amount=amount, category=cat,
            description=desc, date=datetime.now(), is_food=(cat == 'Food'),
            meal_type='Breakfast' if 'breakfast' in desc.lower() else 'Snack' if cat == 'Food' else None
        )
        db.session.add(txn)

    # Create meal plans for today
    meals = [
        ('Breakfast', 'Poha + Chai', 30, 280, 8, 7.5, 'Mess'),
        ('Lunch', 'Dal Rice + Sabzi + Roti', 60, 550, 18, 8.0, 'Mess'),
        ('Snack', 'Banana + Biscuits', 25, 180, 3, 6.0, 'Self'),
        ('Dinner', 'Roti + Paneer + Dal', 70, 480, 20, 8.5, 'Mess'),
    ]
    for meal_type, name, cost, cal, protein, score, source in meals:
        mp = MealPlan(
            user_id=demo_user.id, date=today, meal_type=meal_type,
            name=name, cost=cost, calories=cal, protein=protein,
            nutrition_score=score, source=source
        )
        db.session.add(mp)

    # Create badges
    badges_data = [
        ('first_expense', 'First Step', 'Logged your first expense!', '🎯'),
        ('week_streak', 'Week Warrior', '7-day under-budget streak!', '🔥'),
        ('meal_planner', 'Meal Master', 'Planned meals for a full week', '🍽️'),
        ('budget_setter', 'Budget Boss', 'Set up your first monthly budget', '💰'),
    ]
    for btype, bname, bdesc, bicon in badges_data:
        badge = Badge(
            user_id=demo_user.id, badge_type=btype,
            name=bname, description=bdesc, icon=bicon,
            earned_date=datetime.now() - timedelta(days=random.randint(1, 15))
        )
        db.session.add(badge)

    # Create alerts
    alerts_data = [
        ('savings', '🔥 Great Savings!', 'You saved ₹300 this week! Keep it up!', '🔥'),
        ('budget_warning', '⚠️ Budget Alert', 'You\'ve spent 60% of your monthly budget', '⚠️'),
        ('meal_tip', '💡 Smart Tip', 'Skipping delivery today saves ₹150', '💡'),
        ('daily_summary', '📊 Daily Summary', 'Today\'s spending: ₹100 | Remaining: ₹167', '📊'),
    ]
    for atype, atitle, amsg, aicon in alerts_data:
        alert = Alert(
            user_id=demo_user.id, alert_type=atype,
            title=atitle, message=amsg, icon=aicon
        )
        db.session.add(alert)

    # Create savings goal
    goal = SavingsGoal(
        user_id=demo_user.id,
        name='New Headphones',
        target_amount=2000.0,
        current_amount=850.0,
        deadline=today + timedelta(days=45)
    )
    db.session.add(goal)

    db.session.commit()
