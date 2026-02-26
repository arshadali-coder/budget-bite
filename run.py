import os

# Allow OAuth over HTTP for local development
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

from dotenv import load_dotenv
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
