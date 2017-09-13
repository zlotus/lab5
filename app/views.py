import time
import flask
import json
from flask import request, jsonify, Response
from flask_security import login_required
from flask_security.utils import verify_password
from app import app
from app.utils import set_debug_response_header
from app import user_datastore
from config import DIST_DIR
from app import app_models


@app.route('/', methods=['GET'])
@app.route('/login', methods=['GET'])
def entry_html():
    return set_debug_response_header(flask.send_from_directory(DIST_DIR, 'index.html', mimetype='text/javascript'),
                                     options={'Content-Type': 'text/html'})


@app.route('/<path:path>', methods=['GET'])
def entry_css(path):
    print(path)
    return flask.send_from_directory(DIST_DIR, path)


# @app.route('/index.html', methods=['GET'])
# def entry_js():
#     return flask.send_from_directory(DIST_DIR, 'index.js', mimetype='text/javascript')
#
#
# @app.route('/0.async.js', methods=['GET'])
# def entry_0_async_js():
#     return flask.send_from_directory(DIST_DIR, '0.async.js', mimetype='text/javascript')


@app.route('/api/v1/session/', methods=['GET', 'POST', 'OPTIONS', 'DELETE'])
def session_service():
    resp = jsonify(success=False)
    if request.method == 'DELETE':
        resp = jsonify(success=True)
        resp.set_cookie(key="token", expires=0)
        return set_debug_response_header(resp)
    if request.method == 'POST':
        username, password = request.json['username'], request.json['password']
        user = user_datastore.get_user(username)
        password_hash = user.password
        if verify_password(password, password_hash):
            print('user login: %s' % user.user_name + ' verified')
            resp = jsonify(success=True, userID=user.id)
            resp.set_cookie(key="token",
                            value=str({"id": user.id, "deadline": (time.time() + 86400) * 1000}),
                            max_age=7200,
                            httponly=True)
            return set_debug_response_header(resp)
        else:
            resp = jsonify(success=False, loginError='用户名或密码错误')
            return set_debug_response_header(resp)
    elif request.method == 'GET':
        token, deadline, user_id, user = None, None, None, None
        if not request.cookies:
            resp = jsonify(success=False, loginError='未登录')
            return set_debug_response_header(resp)
        else:
            cookies = request.cookies

        if not cookies.get('token'):
            resp = jsonify(success=False, loginError='未登录')
            return set_debug_response_header(resp)
        else:
            token = json.loads(cookies['token'].replace('\'', '"'))

        if not token.get('deadline') or not token.get('id'):
            resp = jsonify(success=False, loginError='未登录')
            return set_debug_response_header(resp)
        else:
            deadline = int(token['deadline'])
            user_id = int(token['id'])
            user = app_models.User.query.get(user_id)

        if time.time() > (deadline / 1000):
            resp = jsonify(success=False, loginError='会话过期')
            return set_debug_response_header(resp)
        if user:
            result = {
                'success': True,
                'user': {
                    'userID': user.id,
                    'userName': user.user_name,
                    'permissions': [p.name for p in user.roles]
                }
            }
            resp = Response(json.dumps(result))
            return set_debug_response_header(resp)
    elif request.method == 'OPTIONS':
        pass

    return set_debug_response_header(resp)
