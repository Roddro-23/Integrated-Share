from flask_sqlalchemy import SQLAlchemy

# Single db instance shared across all modules.
# Initialised (bound to the app) in app.py via db.init_app(app).
db = SQLAlchemy()
