from datetime import datetime, date
import json
from flask_login import UserMixin
from app.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    avatar = db.Column(db.String(500), default='')
    monthly_budget = db.Column(db.Float, default=5000.0)
    living_type = db.Column(db.String(20), default='Hostel')
    food_preference = db.Column(db.String(20), default='Vegetarian')
    phone = db.Column(db.String(15), nullable=True)
    onboarding_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    meal_plans = db.relationship('MealPlan', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    badges = db.relationship('Badge', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def get_current_budget(self):
        today = date.today()
        budget = Budget.query.filter_by(
            user_id=self.id,
            month=today.month,
            year=today.year
        ).first()
        return budget

    def get_today_spent(self):
        today = date.today()
        result = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.id,
            db.func.date(Transaction.date) == today
        ).scalar()
        return result or 0.0

    def get_month_spent(self):
        today = date.today()
        result = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.id,
            db.extract('month', Transaction.date) == today.month,
            db.extract('year', Transaction.date) == today.year
        ).scalar()
        return result or 0.0

    def get_daily_limit(self):
        import calendar
        today = date.today()
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        remaining_days = days_in_month - today.day + 1
        remaining_budget = self.monthly_budget - self.get_month_spent()
        if remaining_days <= 0:
            return 0
        return round(remaining_budget / remaining_days, 2)

    def get_streak(self):
        """Calculate current savings streak (days under budget)."""
        today = date.today()
        streak = 0
        for i in range(30):
            check_date = date(today.year, today.month, today.day - i) if today.day - i > 0 else None
            if check_date is None:
                break
            daily_spent = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.user_id == self.id,
                db.func.date(Transaction.date) == check_date
            ).scalar() or 0
            if daily_spent <= self.get_daily_limit():
                streak += 1
            else:
                break
        return streak


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Misc')
    subcategory = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(200), default='')
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_food = db.Column(db.Boolean, default=False)
    meal_type = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'subcategory': self.subcategory,
            'description': self.description,
            'date': self.date.isoformat(),
            'is_food': self.is_food,
            'meal_type': self.meal_type
        }


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    food_allocation = db.Column(db.Float, default=0.0)
    travel_allocation = db.Column(db.Float, default=0.0)
    academic_allocation = db.Column(db.Float, default=0.0)
    entertainment_allocation = db.Column(db.Float, default=0.0)
    emergency_reserve = db.Column(db.Float, default=0.0)
    _categories_json = db.Column('categories_json', db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def categories(self):
        return json.loads(self._categories_json) if self._categories_json else {}

    @categories.setter
    def categories(self, value):
        self._categories_json = json.dumps(value)


class MealPlan(db.Model):
    __tablename__ = 'meal_plans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Float, default=0)
    nutrition_score = db.Column(db.Float, default=0)
    source = db.Column(db.String(50), default='Mess')
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'meal_type': self.meal_type,
            'name': self.name,
            'cost': self.cost,
            'calories': self.calories,
            'protein': self.protein,
            'nutrition_score': self.nutrition_score,
            'source': self.source,
            'is_completed': self.is_completed
        }


class SavingsGoal(db.Model):
    __tablename__ = 'savings_goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    deadline = db.Column(db.Date, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progress(self):
        if self.target_amount <= 0:
            return 100
        return round((self.current_amount / self.target_amount) * 100, 1)


class Badge(db.Model):
    __tablename__ = 'badges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), default='')
    icon = db.Column(db.String(50), default='🏆')
    earned_date = db.Column(db.DateTime, default=datetime.utcnow)


class BillSplit(db.Model):
    __tablename__ = 'bill_splits'

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    _participants_json = db.Column('participants_json', db.Text, default='[]')
    split_type = db.Column(db.String(20), default='equal')
    is_settled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref='created_splits')

    @property
    def participants(self):
        return json.loads(self._participants_json) if self._participants_json else []

    @participants.setter
    def participants(self, value):
        self._participants_json = json.dumps(value)


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    icon = db.Column(db.String(10), default='🔔')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'title': self.title,
            'message': self.message,
            'icon': self.icon,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }
