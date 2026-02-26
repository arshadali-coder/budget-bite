from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Budget, Transaction
from datetime import date
import calendar
import json

budget_bp = Blueprint('budget', __name__, template_folder='templates')


@budget_bp.route('/')
@login_required
def index():
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    remaining_days = days_in_month - today.day + 1

    budget = current_user.get_current_budget()
    month_spent = current_user.get_month_spent()
    daily_limit = current_user.get_daily_limit()
    today_spent = current_user.get_today_spent()

    # Category-wise spending
    category_spending = db.session.query(
        Transaction.category, db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).group_by(Transaction.category).all()

    cat_spent = {cat: float(amt) for cat, amt in category_spending}
    cat_allocations = budget.categories if budget else {}

    # Budget pace analysis
    expected_spend = (current_user.monthly_budget / days_in_month) * today.day
    pace_diff = expected_spend - month_spent
    if pace_diff > 0:
        pace_status = 'under'
        pace_message = f'₹{pace_diff:.0f} under expected pace 🎉'
    else:
        pace_status = 'over'
        pace_message = f'₹{abs(pace_diff):.0f} over expected pace ⚠️'

    return render_template('budget/index.html',
        budget=budget,
        month_spent=month_spent,
        daily_limit=daily_limit,
        today_spent=today_spent,
        remaining_days=remaining_days,
        days_in_month=days_in_month,
        cat_spent=cat_spent,
        cat_allocations=cat_allocations,
        pace_status=pace_status,
        pace_message=pace_message,
        expected_spend=expected_spend,
    )


@budget_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    if request.method == 'POST':
        total = float(request.form.get('total_amount', 5000))
        current_user.monthly_budget = total
        db.session.commit()

        today = date.today()
        budget = Budget.query.filter_by(
            user_id=current_user.id, month=today.month, year=today.year
        ).first()

        if not budget:
            budget = Budget(user_id=current_user.id, month=today.month, year=today.year, total_amount=total)
            db.session.add(budget)

        budget.total_amount = total
        budget.food_allocation = float(request.form.get('food_allocation', total * 0.5))
        budget.travel_allocation = float(request.form.get('travel_allocation', total * 0.18))
        budget.academic_allocation = float(request.form.get('academic_allocation', total * 0.12))
        budget.entertainment_allocation = float(request.form.get('entertainment_allocation', total * 0.12))
        budget.emergency_reserve = float(request.form.get('emergency_reserve', total * 0.08))

        budget.categories = {
            'Food': budget.food_allocation,
            'Travel': budget.travel_allocation,
            'Academic': budget.academic_allocation,
            'Entertainment': budget.entertainment_allocation,
            'Misc': total - budget.food_allocation - budget.travel_allocation - budget.academic_allocation - budget.entertainment_allocation - budget.emergency_reserve
        }

        db.session.commit()
        flash('Budget updated successfully! 💰', 'success')
        return redirect(url_for('budget.index'))

    budget = current_user.get_current_budget()
    return render_template('budget/setup.html', budget=budget)


@budget_bp.route('/api/category-data')
@login_required
def category_data():
    today = date.today()
    spending = db.session.query(
        Transaction.category, db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).group_by(Transaction.category).all()

    return jsonify([{'category': cat, 'amount': float(amt)} for cat, amt in spending])
