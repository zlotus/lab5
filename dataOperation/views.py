import flask
import json, os
from flask import request
from pprint import pprint
from app import app
from app import db
from config import ALLOWED_EXTENSIONS, UPLOAD_DATA_FOLDER
from dataOperation import models
from datetime import datetime
from werkzeug.utils import secure_filename


@app.route('/')
@app.route('/index')
def index():
    return 'hello world!'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_data(data):

    def _data2db(data_str):
        data_body = data_str.split('Curve Values:')[1].split('Results:')[0].strip()
        data_lines = data_body.splitlines()[2:]
        for line in data_lines:
            print(line.split())

    data_fragments = data.split('Curve Name')
    e_prime, tan_delta = '', ''
    for fragment in data_fragments:
        if "E'(Modulus)" in fragment:
            e_prime = fragment
        elif 'Tan Delta' in fragment:
            tan_delta = fragment
    _data2db(e_prime)


@app.route('/api/v1/dataOperation/tests/data', methods=['POST'])
def test_data_service():

    def _data2db(data_string, test, data_type="E'"):
        data_body = data_string.split('Curve Values:')[1].split('Results:')[0].strip()
        data_lines = data_body.splitlines()[2:]
        for line in data_lines:
            row = line.split()
            test.test_data.append(models.TestData(sequence_id=row[0],
                                                  x_value=row[2],
                                                  y_value=row[3],
                                                  data_type=data_type,
                                                  date=datetime.now()))

        db.session.commit()

    resp = flask.Response(json.dumps({'status': 'success'}))
    if request.method == 'POST':
        if request.is_xhr:
            file = request.files['datafile']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                test_id = request.form['testID']
                dirpath = os.path.join(UPLOAD_DATA_FOLDER, test_id)
                os.makedirs(dirpath, exist_ok=True)
                filepath = os.path.join(dirpath, filename)
                file.save(filepath)
                resp = flask.Response(json.dumps({'status': 'success', 'url': filepath}))
                test = models.Test.query.get(int(test_id))
                test.test_data_filepath = filepath
                db.session.commit()
                with open(filepath, encoding='utf-16') as data:
                    data_fragments = data.read().split('Curve Name')[1:4]
                    e_prime, tan_delta = '', ''
                    for fragment in data_fragments:
                        if "E'(Modulus)" in fragment:
                            e_prime = fragment
                        elif "E'(Modulus)" not in fragment and 'E"(Modulus)' not in fragment:
                            tan_delta = fragment
                    _data2db(e_prime, test)
                    _data2db(tan_delta, test, 'Tan Delta')

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    resp.headers['Access-Control-Allow-Headers'] = ['Origin', 'Content-Type', 'X-Auth-Token']
    return resp


@app.route('/api/v1/dataOperation/tests', methods=['GET', 'POST'])
def test_service():
    resp = flask.Response(json.dumps({'status': 'success'}))
    if request.method == 'GET':
        tests = []
        test_rs = models.Test.query.all()
        for test_r in test_rs:
            tests.append(test_r)
        resp = flask.Response(json.dumps({'status': 'success', 'tests': tests}))
    elif request.method == 'POST':
        if request.is_json:
            temperature, temperature_min, temperature_max = 0, 0, 0
            frequency, frequency_min, frequency_max = 0, 0, 0
            measure_type = request.json['measureType']
            if measure_type == 'temperature':
                frequency_min = frequency_max = request.json['frequencyMin']
                temperature_min = request.json['temperatureMin']
                temperature_max = request.json['temperatureMax']
            elif measure_type == 'frequency':
                temperature_min = temperature_max = request.json['temperatureMin']
                frequency_min = request.json['frequencyMin']
                frequency_max = request.json['frequencyMax']
            test = models.Test(name=request.json['name'],
                               measure_type=measure_type,
                               thickness=request.json['thickness'],
                               temperature_max=temperature_max,
                               temperature_min=temperature_min,
                               frequency_max=frequency_max,
                               frequency_min=frequency_min,
                               test_type=request.json['testType'],
                               formulation_id=request.json['selectedFormulationID'],
                               date=datetime.now())
            db.session.add(test)
            db.session.commit()
            resp = flask.Response(json.dumps({'status': 'success',
                                              'test_id': test.id,
                                              'test_name': test.name}))

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    resp.headers['Access-Control-Allow-Headers'] = ['Origin', 'Content-Type', 'X-Auth-Token']
    return resp


@app.route('/api/v1/dataOperation/formulations', methods=['GET', 'POST'])
def formulation_service():
    resp = flask.Response(json.dumps({'status': 'success'}))
    if request.method == 'GET':
        formulations = []
        formulations_rs = models.Formulation.query.all()
        for formulation_r in formulations_rs:
            formulation_properties = []
            formulations_property_rs = formulation_r.formulation_property.all()
            for formulations_property_r in formulations_property_rs:
                formulation_properties.append({formulations_property_r.key: formulations_property_r.value})

            formulations.append({
                'id': formulation_r.id,
                'name': formulation_r.name,
                'formulation_properties': formulation_properties
            })
        resp = flask.Response(json.dumps({'formulations': formulations}))
    elif request.method == 'POST':
        if request.is_json:
            formulation_property_dict = request.json
            formulation_property_list, formulation_property_key_list = [], []
            formulation_name = formulation_property_dict.pop('name', 'formulation-%f' % datetime.now().timestamp())
            formulation_property_key_list = [x for x in formulation_property_dict if x.startswith('key-')]
            formulation_property_key_list.sort(key=lambda x: int(x.replace('key-', '')))
            for fpkey in formulation_property_key_list:
                key = formulation_property_dict[fpkey]
                val = formulation_property_dict['value-%s' % fpkey.split('-', maxsplit=1)[1]]
                formulation_property_list.append((key, val))
            # create new formulation in db
            formulation = models.Formulation(name=formulation_name, date=datetime.now())
            db.session.add(formulation)
            db.session.commit()
            for fpkey, fpval in formulation_property_list:
                formulation.formulation_property.append(models.FormulationProperty(key=fpkey, value=fpval))
            db.session.commit()
            resp = flask.Response(json.dumps({'status': 'success',
                                              'new_formulation_id': formulation.id,
                                              'new_formulation_name': formulation.name}))

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    resp.headers['Access-Control-Allow-Headers'] = ['Origin', 'Content-Type', 'X-Auth-Token']
    return resp
