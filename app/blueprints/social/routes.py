from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import BillSplit, User
import json

social_bp = Blueprint('social', __name__, template_folder='templates')


@social_bp.route('/')
@login_required
def index():
    my_splits = BillSplit.query.filter_by(creator_id=current_user.id)\
        .order_by(BillSplit.created_at.desc()).all()
    return render_template('social/index.html', splits=my_splits)


@social_bp.route('/split/create', methods=['GET', 'POST'])
@login_required
def create_split():
    if request.method == 'POST':
        title = request.form.get('title', 'Bill Split')
        total = float(request.form.get('total_amount', 0))
        names = request.form.getlist('participant_name')
        split_type = request.form.get('split_type', 'equal')

        if total <= 0:
            flash('Amount must be greater than zero!', 'error')
            return redirect(url_for('social.create_split'))

        participants = []
        per_person = total / max(1, len(names) + 1)

        for name in names:
            if name.strip():
                participants.append({
                    'name': name.strip(),
                    'share': round(per_person, 2),
                    'paid': False
                })

        # Add creator
        participants.append({
            'name': current_user.name,
            'share': round(per_person, 2),
            'paid': True,
            'is_creator': True
        })

        split = BillSplit(
            creator_id=current_user.id,
            title=title,
            total_amount=total,
            split_type=split_type
        )
        split.participants = participants
        db.session.add(split)
        db.session.commit()

        flash(f'Bill split created: {title} (₹{total:.0f}) 🤝', 'success')
        return redirect(url_for('social.index'))

    return render_template('social/create_split.html')


@social_bp.route('/split/<int:split_id>')
@login_required
def view_split(split_id):
    split = BillSplit.query.filter_by(id=split_id, creator_id=current_user.id).first_or_404()
    return render_template('social/view_split.html', split=split)


@social_bp.route('/split/<int:split_id>/settle/<int:idx>', methods=['POST'])
@login_required
def settle_participant(split_id, idx):
    split = BillSplit.query.filter_by(id=split_id, creator_id=current_user.id).first_or_404()
    participants = split.participants
    if 0 <= idx < len(participants):
        participants[idx]['paid'] = True
        split.participants = participants
        all_paid = all(p.get('paid', False) for p in participants)
        split.is_settled = all_paid
        db.session.commit()
        flash(f'{participants[idx]["name"]} marked as paid! ✅', 'success')
    return redirect(url_for('social.view_split', split_id=split_id))


@social_bp.route('/split/<int:split_id>/delete', methods=['POST'])
@login_required
def delete_split(split_id):
    split = BillSplit.query.filter_by(id=split_id, creator_id=current_user.id).first_or_404()
    db.session.delete(split)
    db.session.commit()
    flash('Bill split deleted! 🗑️', 'info')
    return redirect(url_for('social.index'))
