import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///budget_bite.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Fix Postgres URI prefix (Vercel/Heroku sometimes provide postgres:// instead of postgresql://)
    @classmethod
    def fix_db_url(cls):
        url = os.environ.get('DATABASE_URL', '')
        if url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql://', 1)
        return url or 'sqlite:///budget_bite.db'

    # Session cookie settings — secure on Vercel (HTTPS), not on localhost
    SESSION_COOKIE_SECURE = os.environ.get('VERCEL', False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # App settings
    DEFAULT_CURRENCY = '₹'
    CATEGORIES = ['Food', 'Travel', 'Academic', 'Entertainment', 'Shopping', 'Health', 'Misc']
    FOOD_SUBCATEGORIES = ['Mess', 'Canteen', 'Restaurant', 'Delivery', 'Groceries', 'Snacks', 'Beverages']
    MEAL_TYPES = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
    LIVING_TYPES = ['Hostel', 'PG', 'Home', 'Flat']
    FOOD_PREFERENCES = ['Vegetarian', 'Non-Vegetarian', 'Vegan', 'Eggetarian']


# Apply DB URL fix at import time
Config.SQLALCHEMY_DATABASE_URI = Config.fix_db_url()
