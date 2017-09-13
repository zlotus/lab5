CSRF_ENABLED = False
SECRET_KEY = 'you-will-never-guess'

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(BASE_DIR, 'db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
SECURITY_TRACKABLE = True
SECURITY_PASSWORD_SALT = 'lab5_app'
SECURITY_USER_IDENTITY_ATTRIBUTES = 'user_name'
SECURITY_LOGIN_URL = '/unreachable'

UPLOAD_FOLDER = './test_data'
MODEL_FOLDER = './models'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png'}
