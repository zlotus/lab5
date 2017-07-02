from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from celery import Celery


app = Flask(__name__)

app.config.from_object('config')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
celery = Celery('fit_task', broker='redis://localhost:6379')

from dataOperation import views, models
from dataAnalysis import views