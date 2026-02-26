from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Transaction
from datetime import date, timedelta
import calendar

analytics_bp = Blueprint('analytics', __name__, template_folder='templates')


@analytics_bp.route('/')
@login_required
def index():
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    # Monthly spending data (daily)
    daily_spending = []
    for day in range(1, today.day + 1):
        d = date(today.year, today.month, day)
        spent = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            db.func.date(Transaction.date) == d
        ).scalar() or 0
        daily_spending.append({'day': day, 'date': d.isoformat(), 'amount': float(spent)})

    # Category distribution
    category_dist = db.session.query(
        Transaction.category, db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).group_by(Transaction.category).all()

    # Food breakdown
    food_breakdown = db.session.query(
        Transaction.subcategory, db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.is_food == True,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).group_by(Transaction.subcategory).all()

    # Weekday vs Weekend
    weekday_total = 0
    weekend_total = 0
    weekday_count = 0
    weekend_count = 0
    for day in range(1, today.day + 1):
        d = date(today.year, today.month, day)
        spent = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            db.func.date(Transaction.date) == d
        ).scalar() or 0
        if d.weekday() < 5:
            weekday_total += (spent or 0)
            weekday_count += 1
        else:
            weekend_total += (spent or 0)
            weekend_count += 1

    weekday_avg = weekday_total / max(1, weekday_count)
    weekend_avg = weekend_total / max(1, weekend_count)

    # Week-over-week comparison
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    this_week_spent = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        db.func.date(Transaction.date) >= this_week_start,
        db.func.date(Transaction.date) <= today
    ).scalar() or 0

    last_week_spent = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        db.func.date(Transaction.date) >= last_week_start,
        db.func.date(Transaction.date) <= last_week_end
    ).scalar() or 0

    week_change = this_week_spent - last_week_spent
    week_change_pct = (week_change / max(1, last_week_spent)) * 100

    # Month spent & average
    month_spent = current_user.get_month_spent()
    daily_avg = month_spent / max(1, today.day)

    # Top expense
    top_expense = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).order_by(Transaction.amount.desc()).first()

    # Behavioral insights
    insights = []
    if weekend_avg > weekday_avg * 1.3:
        insights.append({
            'type': 'warning',
            'icon': '📅',
            'text': f'Weekend spending is {((weekend_avg/max(1,weekday_avg))-1)*100:.0f}% higher than weekdays'
        })

    food_total = sum(amt for _, amt in category_dist if _ == 'Food')
    total_spent = sum(amt for _, amt in category_dist)
    if total_spent > 0 and food_total / total_spent > 0.6:
        insights.append({
            'type': 'info',
            'icon': '🍕',
            'text': f'Food makes up {food_total/total_spent*100:.0f}% of spending — try mess meals to save'
        })

    if week_change > 0:
        insights.append({
            'type': 'warning',
            'icon': '📈',
            'text': f'Spending is up ₹{week_change:.0f} vs last week'
        })
    else:
        insights.append({
            'type': 'success',
            'icon': '📉',
            'text': f'Great! Spending is down ₹{abs(week_change):.0f} vs last week'
        })

    return render_template('analytics/index.html',
        daily_spending=daily_spending,
        category_dist=[(cat, float(amt)) for cat, amt in category_dist],
        food_breakdown=[(sub or 'Unknown', float(amt)) for sub, amt in food_breakdown],
        weekday_avg=weekday_avg,
        weekend_avg=weekend_avg,
        this_week_spent=this_week_spent,
        last_week_spent=last_week_spent,
        week_change=week_change,
        week_change_pct=week_change_pct,
        month_spent=month_spent,
        daily_avg=daily_avg,
        top_expense=top_expense,
        insights=insights,
        days_in_month=days_in_month,
    )
