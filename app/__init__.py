from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security.utils import hash_password

app = Flask(__name__)

app.config.from_object('config')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
celery = Celery('fit_task', broker='redis://localhost:6379')

from dataOperation import models as do_models
from app import models as app_models

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, app_models.User, app_models.Role)
security = Security(app, user_datastore)


# Create a user to test with
@app.before_first_request
def before_first_request():
    # Create any database tables that don't exist yet.
    db.create_all()

    # Create the Roles "admin" and "end-user" -- unless they already exist
    user_datastore.find_or_create_role(name='dashboard', description='Overview of test data in database')
    user_datastore.find_or_create_role(name='dataOperation', description='The root of Data operation')
    user_datastore.find_or_create_role(name='dataOperation/uploader', description='Upload data')
    user_datastore.find_or_create_role(name='dataOperation/viewer', description='Visualize data in 2D or 3D plots')
    user_datastore.find_or_create_role(name='dataOperation/searcher',
                                       description='Searching data with specific conditions')
    user_datastore.find_or_create_role(name='dataAnalysis', description='Analysing data with neural network')
    user_datastore.find_or_create_role(name='users', description='User management')

    # Create two Users for testing purposes -- unless they already exists.
    # In each case, use Flask-Security utility function to encrypt the password.
    if not user_datastore.get_user('admin'):
        user_datastore.create_user(email='admin@623.com', user_name='admin', password=hash_password('admin'))
    if not user_datastore.get_user('guest'):
        user_datastore.create_user(email='guest@623.com', user_name='guest@623.com', password=hash_password('guest@623.com'))

    # Commit any database changes; the User and Roles must exist before we can add a Role to the User
    db.session.commit()

    # Give one User has the "end-user" role, while the other has the "admin" role. (This will have no effect if the
    # Users already have these Roles.) Again, commit any database changes.
    user_datastore.add_role_to_user('admin@623.com', 'dashboard')
    user_datastore.add_role_to_user('admin@623.com', 'dataOperation')
    user_datastore.add_role_to_user('admin@623.com', 'dataOperation/uploader')
    user_datastore.add_role_to_user('admin@623.com', 'dataOperation/viewer')
    user_datastore.add_role_to_user('admin@623.com', 'dataOperation/searcher')
    user_datastore.add_role_to_user('admin@623.com', 'dataAnalysis')
    user_datastore.add_role_to_user('admin@623.com', 'users')
    user_datastore.add_role_to_user('guest@623.com', 'dashboard')
    user_datastore.add_role_to_user('guest@623.com', 'dataOperation')
    user_datastore.add_role_to_user('guest@623.com', 'dataOperation/viewer')
    db.session.commit()


from dataOperation import views as do_views
from app import views as app_views
from dataAnalysis import views as  da_views
