from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from app.extensions import db
from app.models import User
from datetime import date

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Single OAuth instance — initialized once via init_oauth(app)
oauth = OAuth()
_google_registered = False


def init_oauth(app):
    """Call once from the app factory to register Google OAuth."""
    global _google_registered
    oauth.init_app(app)
    if not _google_registered:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile',
                'prompt': 'select_account',
            }
        )
        _google_registered = True


@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return render_template('auth/login.html')


@auth_bp.route('/google/login')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        flash(f'Google login failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo')
    if not userinfo:
        flash('Could not retrieve user info from Google.', 'error')
        return redirect(url_for('auth.login'))

    google_id = userinfo['sub']
    email = userinfo['email']
    name = userinfo.get('name', email.split('@')[0])
    avatar = userinfo.get('picture', '')

    # Find by Google ID first, then fall back to email
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        # New sign-up
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
        # Returning user — refresh avatar & google_id
        user.google_id = google_id
        user.avatar = avatar
        user.name = name
        db.session.commit()
        login_user(user)
        flash(f'Welcome back, {name}! 👋', 'success')
        if not user.onboarding_complete:
            return redirect(url_for('auth.onboarding'))
        return redirect(url_for('dashboard.home'))


@auth_bp.route('/demo-login')
def demo_login():
    user = User.query.filter_by(email='demo@budgetbite.app').first()
    if user:
        login_user(user)
        flash('Welcome, Alex! 👋 You\'re in the demo account.', 'success')
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
            'Food': total * 0.50, 'Travel': total * 0.18,
            'Academic': total * 0.12, 'Entertainment': total * 0.12,
            'Misc': total * 0.08
        }
        db.session.add(budget)
        db.session.commit()
        flash('Budget set up! Your journey starts now 🚀', 'success')
        return redirect(url_for('dashboard.home'))

    return render_template('auth/onboarding.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You\'ve been logged out. See you soon! 👋', 'info')
    return redirect(url_for('auth.login'))
