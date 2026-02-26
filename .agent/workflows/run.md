---
description: How to run the Budget Bite application locally
---

## Prerequisites
- Python 3.8+ installed
- pip available

## Steps

// turbo
1. Install dependencies
```
pip install -r requirements.txt
```

// turbo
2. Run the Flask development server
```
python run.py
```

3. Open the app in browser at http://127.0.0.1:5000

4. Click "Quick Demo Login" to explore with pre-loaded data

## Notes
- The app uses SQLite by default (auto-created)
- Demo user is seeded automatically on first run
- To reset data, delete `instance/budget_bite.db` and restart
