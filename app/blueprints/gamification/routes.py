from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Badge, SavingsGoal, Transaction
from datetime import date, timedelta

gamification_bp = Blueprint('gamification', __name__, template_folder='templates')

AVAILABLE_BADGES = [
    {'type': 'first_expense', 'name': 'First Step', 'desc': 'Log your first expense', 'icon': '🎯', 'condition': 'first_txn'},
    {'type': 'week_streak', 'name': 'Week Warrior', 'desc': '7-day under-budget streak', 'icon': '🔥', 'condition': 'streak_7'},
    {'type': 'month_streak', 'name': 'Monthly Master', 'desc': '30-day under-budget streak', 'icon': '👑', 'condition': 'streak_30'},
    {'type': 'meal_planner', 'name': 'Meal Master', 'desc': 'Plan meals for a full week', 'icon': '🍽️', 'condition': 'meal_plan'},
    {'type': 'budget_setter', 'name': 'Budget Boss', 'desc': 'Set up your monthly budget', 'icon': '💰', 'condition': 'budget_set'},
    {'type': 'saver_100', 'name': 'Penny Pincher', 'desc': 'Save ₹100 in a day', 'icon': '🪙', 'condition': 'daily_save_100'},
    {'type': 'saver_500', 'name': 'Smart Saver', 'desc': 'Save ₹500 in a week', 'icon': '💎', 'condition': 'weekly_save_500'},
    {'type': 'goal_complete', 'name': 'Goal Getter', 'desc': 'Complete a savings goal', 'icon': '🏆', 'condition': 'goal_done'},
    {'type': 'social_butterfly', 'name': 'Social Butterfly', 'desc': 'Split your first bill', 'icon': '🦋', 'condition': 'first_split'},
    {'type': 'food_tracker', 'name': 'Food Tracker', 'desc': 'Log 50 food expenses', 'icon': '📝', 'condition': 'food_50'},
]


@gamification_bp.route('/')
@login_required
def index():
    earned_badges = Badge.query.filter_by(user_id=current_user.id).all()
    earned_types = {b.badge_type for b in earned_badges}

    all_badges = []
    for badge_def in AVAILABLE_BADGES:
        all_badges.append({
            **badge_def,
            'earned': badge_def['type'] in earned_types,
            'earned_date': next((b.earned_date for b in earned_badges if b.badge_type == badge_def['type']), None)
        })

    # Savings goals
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.created_at.desc()).all()

    # Streak
    streak = current_user.get_streak()

    # Total savings this month
    month_spent = current_user.get_month_spent()
    today = date.today()
    expected_by_now = (current_user.monthly_budget / 30) * today.day
    savings_this_month = max(0, expected_by_now - month_spent)

    return render_template('gamification/index.html',
        all_badges=all_badges,
        earned_count=len(earned_badges),
        total_badges=len(AVAILABLE_BADGES),
        goals=goals,
        streak=streak,
        savings_this_month=savings_this_month,
    )


@gamification_bp.route('/goal/add', methods=['POST'])
@login_required
def add_goal():
    from flask import request
    name = request.form.get('name', 'My Goal')
    target = float(request.form.get('target_amount', 1000))
    deadline = request.form.get('deadline', '')

    goal = SavingsGoal(
        user_id=current_user.id,
        name=name,
        target_amount=target,
        deadline=date.fromisoformat(deadline) if deadline else None
    )
    db.session.add(goal)
    db.session.commit()
    flash(f'Goal created: {name} (₹{target:.0f}) 🎯', 'success')
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/goal/<int:goal_id>/update', methods=['POST'])
@login_required
def update_goal(goal_id):
    from flask import request
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    add_amount = float(request.form.get('add_amount', 0))
    goal.current_amount += add_amount
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True
        flash(f'🎉 Goal "{goal.name}" completed! Amazing!', 'success')
    else:
        flash(f'Added ₹{add_amount:.0f} to {goal.name}! Progress: {goal.progress}%', 'success')
    db.session.commit()
    return redirect(url_for('gamification.index'))


@gamification_bp.route('/goal/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash('Goal deleted! 🗑️', 'info')
    return redirect(url_for('gamification.index'))
