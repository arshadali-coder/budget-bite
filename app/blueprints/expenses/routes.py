from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Transaction, Alert
from datetime import datetime, date

expenses_bp = Blueprint('expenses', __name__, template_folder='templates')


@expenses_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', 'all')
    date_filter = request.args.get('date', '')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    if date_filter:
        query = query.filter(db.func.date(Transaction.date) == date_filter)

    transactions = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=15, error_out=False)

    # Category totals for current month
    today = date.today()
    category_totals = db.session.query(
        Transaction.category, db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        db.extract('month', Transaction.date) == today.month,
        db.extract('year', Transaction.date) == today.year
    ).group_by(Transaction.category).all()

    return render_template('expenses/index.html',
        transactions=transactions,
        category_totals=dict(category_totals),
        current_filter=category_filter,
        date_filter=date_filter
    )


@expenses_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', 'Misc')
        description = request.form.get('description', '')
        subcategory = request.form.get('subcategory', '')
        is_food = category == 'Food'
        meal_type = request.form.get('meal_type', '') if is_food else None
        txn_date = request.form.get('date', '')

        if amount <= 0:
            flash('Amount must be greater than zero!', 'error')
            return redirect(url_for('expenses.add'))

        txn = Transaction(
            user_id=current_user.id,
            amount=amount,
            category=category,
            subcategory=subcategory,
            description=description,
            is_food=is_food,
            meal_type=meal_type,
            date=datetime.strptime(txn_date, '%Y-%m-%d') if txn_date else datetime.now()
        )
        db.session.add(txn)

        # Check for overspending and create alert
        daily_limit = current_user.get_daily_limit()
        today_spent = current_user.get_today_spent() + amount
        if today_spent > daily_limit and daily_limit > 0:
            alert = Alert(
                user_id=current_user.id,
                alert_type='overspend',
                title='⚠️ Daily Limit Exceeded!',
                message=f'You\'ve spent ₹{today_spent:.0f} today, exceeding your ₹{daily_limit:.0f} limit.',
                icon='⚠️'
            )
            db.session.add(alert)

        db.session.commit()
        flash(f'₹{amount:.0f} added to {category}! ✅', 'success')
        return redirect(url_for('expenses.index'))

    return render_template('expenses/add.html', today=date.today().isoformat())


@expenses_bp.route('/delete/<int:txn_id>', methods=['POST'])
@login_required
def delete(txn_id):
    txn = Transaction.query.filter_by(id=txn_id, user_id=current_user.id).first_or_404()
    db.session.delete(txn)
    db.session.commit()
    flash('Transaction deleted! 🗑️', 'info')
    return redirect(url_for('expenses.index'))


@expenses_bp.route('/quick-add', methods=['POST'])
@login_required
def quick_add():
    """AJAX endpoint for quick expense entry."""
    data = request.get_json()
    amount = float(data.get('amount', 0))
    category = data.get('category', 'Misc')
    description = data.get('description', '')

    if amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400

    txn = Transaction(
        user_id=current_user.id,
        amount=amount,
        category=category,
        description=description,
        is_food=(category == 'Food'),
        date=datetime.now()
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        'success': True,
        'transaction': txn.to_dict(),
        'today_spent': current_user.get_today_spent(),
        'daily_limit': current_user.get_daily_limit()
    })
