from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Transaction, MealPlan, Alert, Badge, SavingsGoal
from datetime import date, datetime, timedelta
import calendar

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates')


@dashboard_bp.route('/')
@login_required
def home():
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    remaining_days = days_in_month - today.day + 1

    # Today's data
    today_spent = current_user.get_today_spent()
    month_spent = current_user.get_month_spent()
    daily_limit = current_user.get_daily_limit()
    remaining_budget = current_user.monthly_budget - month_spent

    # Budget health percentage
    budget_used_pct = round((month_spent / current_user.monthly_budget) * 100, 1) if current_user.monthly_budget > 0 else 0
    day_progress_pct = round((today.day / days_in_month) * 100, 1)

    # Determine status
    if budget_used_pct <= day_progress_pct:
        budget_status = 'healthy'
        status_message = "You're on track! 🎉"
    elif budget_used_pct <= day_progress_pct + 15:
        budget_status = 'warning'
        status_message = "Slightly over pace — watch spending ⚠️"
    else:
        budget_status = 'danger'
        status_message = "Overspending alert! Cut back today 🚨"

    # Recent transactions
    recent_txns = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc()).limit(5).all()

    # Today's meals
    today_meals = MealPlan.query.filter_by(user_id=current_user.id, date=today).all()
    total_meal_cost = sum(m.cost for m in today_meals)

    # Category breakdown for today
    category_spending = db.session.query(
        Transaction.category,
        db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).group_by(Transaction.category).all()

    categories_data = {cat: float(amt) for cat, amt in category_spending}

    # Recent alerts
    recent_alerts = Alert.query.filter_by(user_id=current_user.id)\
        .order_by(Alert.created_at.desc()).limit(3).all()

    # Weekly spending data (last 7 days)
    weekly_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        spent = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            db.func.date(Transaction.date) == d
        ).scalar() or 0
        weekly_data.append({
            'day': d.strftime('%a'),
            'date': d.isoformat(),
            'amount': float(spent)
        })

    # Savings goals
    goals = SavingsGoal.query.filter_by(user_id=current_user.id, is_completed=False).all()

    # Badges count
    badge_count = Badge.query.filter_by(user_id=current_user.id).count()

    # Predicted end-of-month balance
    avg_daily = month_spent / today.day if today.day > 0 else 0
    predicted_total = avg_daily * days_in_month
    predicted_balance = current_user.monthly_budget - predicted_total

    # AI insight message
    if predicted_balance < 0:
        days_until_broke = int(remaining_budget / avg_daily) if avg_daily > 0 else remaining_days
        ai_insight = f"At this pace, budget will end in {days_until_broke} days"
        ai_insight_type = 'danger'
    elif budget_used_pct > 80:
        ai_insight = f"You've used {budget_used_pct}% of your budget with {remaining_days} days left"
        ai_insight_type = 'warning'
    else:
        ai_insight = f"Great pace! Predicted savings: ₹{max(0, predicted_balance):.0f} this month"
        ai_insight_type = 'success'

    return render_template('dashboard/home.html',
        today_spent=today_spent,
        month_spent=month_spent,
        daily_limit=daily_limit,
        remaining_budget=remaining_budget,
        budget_used_pct=budget_used_pct,
        budget_status=budget_status,
        status_message=status_message,
        recent_txns=recent_txns,
        today_meals=today_meals,
        total_meal_cost=total_meal_cost,
        categories_data=categories_data,
        recent_alerts=recent_alerts,
        weekly_data=weekly_data,
        goals=goals,
        badge_count=badge_count,
        remaining_days=remaining_days,
        ai_insight=ai_insight,
        ai_insight_type=ai_insight_type,
        predicted_balance=predicted_balance,
        day_progress_pct=day_progress_pct,
    )


@dashboard_bp.route('/api/weekly-data')
@login_required
def weekly_data_api():
    today = date.today()
    data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        spent = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            db.func.date(Transaction.date) == d
        ).scalar() or 0
        data.append({'day': d.strftime('%a'), 'amount': float(spent)})
    return jsonify(data)
