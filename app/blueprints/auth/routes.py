from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from app.extensions import db
from app.models import User
from flask import current_app
import os

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# OAuth instance — registered lazily so we can access app config
oauth = OAuth()


def get_google():
    """Get or register the Google OAuth remote app."""
    if 'google' not in oauth._registry:
        oauth.init_app(current_app._get_current_object())
        oauth.register(
            name='google',
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile',
                'prompt': 'select_account',
            }
        )
    return oauth.google


@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return render_template('auth/login.html')


@auth_bp.route('/google/login')
def google_login():
    """Redirect to Google's OAuth consent screen."""
    redirect_uri = url_for('auth.google_callback', _external=True)
    # Re-init oauth every time to pick up fresh app context
    _init_oauth()
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle the Google OAuth callback, create/login the user."""
    _init_oauth()
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        flash(f'Google login failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo')
    if not userinfo:
        flash('Could not retrieve user information from Google.', 'error')
        return redirect(url_for('auth.login'))

    google_id = userinfo['sub']
    email = userinfo['email']
    name = userinfo.get('name', email.split('@')[0])
    avatar = userinfo.get('picture', '')

    # Find existing user by Google ID or email
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        # New user — create account
        user = User(
            google_id=google_id,
            name=name,
            email=email,
            avatar=avatar,
            onboarding_complete=False,
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f'Welcome to Budget Bite, {name}! 🎉 Let\'s set up your budget.', 'success')
        return redirect(url_for('auth.onboarding'))
    else:
        # Returning user — update info
        user.google_id = google_id
        user.avatar = avatar
        user.name = name
        db.session.commit()
        login_user(user)
        flash(f'Welcome back, {name}! 👋', 'success')
        if not user.onboarding_complete:
            return redirect(url_for('auth.onboarding'))
        return redirect(url_for('dashboard.home'))


def _init_oauth():
    """Initialize/register the Google OAuth client with the current app."""
    oauth.init_app(current_app._get_current_object())
    if 'google' not in oauth._registry:
        oauth.register(
            name='google',
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile',
                'prompt': 'select_account',
            }
        )


@auth_bp.route('/demo-login')
def demo_login():
    """Quick demo login without Google OAuth."""
    user = User.query.filter_by(email='demo@budgetbite.app').first()
    if user:
        login_user(user)
        flash('Welcome, Alex! 👋 Exploring the demo account.', 'success')
        return redirect(url_for('dashboard.home'))
    flash('Demo account not found. Please restart the app.', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        current_user.monthly_budget = float(request.form.get('monthly_budget', 5000))
        current_user.living_type = request.form.get('living_type', 'Hostel')
        current_user.food_preference = request.form.get('food_preference', 'Vegetarian')
        current_user.onboarding_complete = True
        db.session.commit()

        from app.models import Budget
        from datetime import date
        today = date.today()
        total = current_user.monthly_budget
        budget = Budget(
            user_id=current_user.id,
            month=today.month,
            year=today.year,
            total_amount=total,
            food_allocation=total * 0.50,
            travel_allocation=total * 0.18,
            academic_allocation=total * 0.12,
            entertainment_allocation=total * 0.12,
            emergency_reserve=total * 0.08
        )
        budget.categories = {
            'Food': total * 0.50, 'Travel': total * 0.18, 'Academic': total * 0.12,
            'Entertainment': total * 0.12, 'Misc': total * 0.08
        }
        db.session.add(budget)
        db.session.commit()

        flash('Budget set up! Let\'s start your journey 🚀', 'success')
        return redirect(url_for('dashboard.home'))

    return render_template('auth/onboarding.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You\'ve been logged out. See you soon! 👋', 'info')
    return redirect(url_for('auth.login'))
