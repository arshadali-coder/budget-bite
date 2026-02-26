from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Alert
from datetime import datetime

alerts_bp = Blueprint('alerts', __name__, template_folder='templates')


@alerts_bp.route('/')
@login_required
def index():
    alerts = Alert.query.filter_by(user_id=current_user.id)\
        .order_by(Alert.created_at.desc()).limit(50).all()
    return render_template('alerts/index.html', alerts=alerts)


@alerts_bp.route('/mark-read/<int:alert_id>', methods=['POST'])
@login_required
def mark_read(alert_id):
    alert = Alert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    alert.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@alerts_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Alert.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read! ✅', 'success')
    return redirect(url_for('alerts.index'))


@alerts_bp.route('/api/unread-count')
@login_required
def unread_count():
    count = Alert.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})
