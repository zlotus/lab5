from config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def set_debug_response_header(response, options=None):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'HEAD', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Origin,Content-Type,X-Auth-Token,Access-Control-Allow-Origin'
    if options:
        for item in options:
            response.headers[item] = options[item]
    return response
