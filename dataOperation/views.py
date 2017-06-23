import flask
import json
import os
from flask import request
from pprint import pprint
from app import app
from app import db
from dataOperation.utils import allowed_file
from config import UPLOAD_FOLDER
from dataOperation.models import Formulation, FormulationProperty, Test, TestData, TestAttachment
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import func


@app.route('/')
@app.route('/index')
def index():
    return 'hello world!'


############################################################
# dashboard services begin                                 #
############################################################

@app.route('/api/v1/dashboard', methods=['GET'])
def dashboard_service():
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        result = {}
        f = db.session.execute(db.session.query(func.count(Formulation.id))).first()
        result['formulationNumber'] = f[0] if f[0] else 0
        t = db.session.execute(db.session.query(func.count(Test.id))).first()
        result['testNumber'] = t[0] if t[0] else 0
        d = db.session.execute(db.session.query(func.count(TestData.id))).first()
        result['dataNumber'] = d[0] if d[0] else 0
        a = db.session.execute(db.session.query(func.count(TestAttachment.id))).first()
        result['attachmentNumber'] = a[0] if a[0] else 0
        result.update({'status': 'success'})
        resp = flask.Response(json.dumps(result))
        print(resp)

    return resp


############################################################
# dashboard services end                                   #
############################################################

############################################################
# tests services begin                                     #
############################################################


@app.route('/api/v1/dataOperation/tests/<int:test_id>/attachments', methods=['POST', 'DELETE'])
def test_instance_attachment_collection_service(test_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'POST':
        if request.is_xhr:
            file = request.files['attachments']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                dirpath = os.path.join(UPLOAD_FOLDER, str(test_id), 'attachments')
                os.makedirs(dirpath, exist_ok=True)
                filepath = os.path.join(dirpath, filename)
                file.save(filepath)

                # db: update the attachment for the test where test.id = test_id
                test = Test.query.get(test_id)
                test.test_attachment.append(TestAttachment(name=filename, attachment_url=filepath))
                db.session.commit()

                resp = flask.Response(json.dumps({'status': 'success', 'url': filepath}))
    elif request.method == 'DELETE':
        if request.is_json:
            filename = secure_filename(request.json['removedFile'])
            dirpath = os.path.join(UPLOAD_FOLDER, str(test_id), 'attachments')
            filepath = os.path.join(dirpath, filename)
            try:
                os.remove(filepath)
                # db: delete the attachment for the test where test.id = test_id
                TestAttachment.query.filter(
                    (TestAttachment.test_id == test_id) &
                    (TestAttachment.name == filename)
                ).delete()
                db.session.commit()

                resp = flask.Response(json.dumps({'status': 'success', 'url': filepath}))
            except FileNotFoundError:
                print('FileNotFound: ', filepath)
                resp = flask.Response(json.dumps({'status': 'failed', 'url': filepath}))

    return resp


@app.route('/api/v1/dataOperation/tests/<int:test_id>/data', methods=['GET', 'POST', 'DELETE'])
def test_instance_data_collection_service(test_id):

    def _data2db(data_string, test_instance, data_type="E'"):
        data_body = data_string.split('Curve Values:')[1].split('Results:')[0].strip()
        data_lines = data_body.splitlines()[2:]
        for line in data_lines:
            row = line.split()
            test_instance.test_data.append(TestData(sequence_id=row[0],
                                                    x_value=row[-2],
                                                    y_value=row[-1],
                                                    data_type=data_type))

    resp = flask.Response(json.dumps({'status': 'failed'}))
    if test_id <=0:
        return resp

    if request.method == 'GET':
        data_dict = {
            'formulation_id': Test.query.get(test_id).formulation_id,
            'test_id': test_id,
            'test_data': {
                'e_prime': [],
                'tan_delta': []
            }
        }
        print(data_dict)
        # coordinate_name = 'x' if Test.query.get(test_id).measure_type == 'temperature' else 'y'
        td_rs = TestData.query.filter(TestData.test_id == test_id)
        for td_r in td_rs:
            if td_r.data_type.lower() == "e'":
                data_dict['test_data']['e_prime'].append({'x': td_r.x_value, 'y': td_r.y_value})
            elif td_r.data_type.lower() == 'tan delta':
                data_dict['test_data']['tan_delta'].append({'x': td_r.x_value, 'y': td_r.y_value})
        resp = flask.Response(json.dumps({'status': 'success', 'test': data_dict}))
    elif request.method == 'POST':
        # add data file
        if request.is_xhr:
            file = request.files['datafile']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                dirpath = os.path.join(UPLOAD_FOLDER, str(test_id))
                os.makedirs(dirpath, exist_ok=True)
                filepath = os.path.join(dirpath, filename)
                file.save(filepath)

                # db: update the data file path for the test where test.id = test_id
                test = Test.query.get(test_id)
                test.data_file_url = filepath
                db.session.commit()

                with open(filepath, encoding='utf-16') as data:
                    data_fragments = data.read().split('Curve Name')[1:4]
                    e_prime, tan_delta = '', ''
                    for fragment in data_fragments:
                        if "E'(Modulus)" in fragment:
                            e_prime = fragment
                        elif "E'(Modulus)" not in fragment and 'E"(Modulus)' not in fragment:
                            tan_delta = fragment

                    # db: delete all TestData for the test where test.id = test_id
                    TestData.query.filter(TestData.test_id == test_id).delete()
                    db.session.commit()

                    # db: append E' data for the test where test.id = test_id
                    _data2db(e_prime, test, "E'")
                    db.session.commit()

                    # db: append Tan Delta data for the test where test.id = test_id
                    _data2db(tan_delta, test, 'Tan Delta')
                    db.session.commit()

                    resp = flask.Response(json.dumps({'status': 'success', 'url': filepath}))
    elif request.method == 'DELETE':
        if request.is_json:
            filename = secure_filename(request.json['removedFile'])
            dirpath = os.path.join(UPLOAD_FOLDER, str(test_id))
            filepath = os.path.join(dirpath, filename)

            # db: delete all TestData for the test where test.id = test_id
            TestData.query.filter(TestData.test_id == test_id).delete()
            db.session.commit()

            # db: delete the data file path for the test where test.id = test_id
            test = Test.query.get(test_id)
            test.test_data_filepath = ''
            db.session.commit()

            try:
                os.remove(filepath)
                resp = flask.Response(json.dumps({'status': 'success', 'url': filepath}))
            except FileNotFoundError:
                print('FileNotFound: ', filepath)
                resp = flask.Response(json.dumps({'status': 'failed', 'url': filepath}))

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    resp.headers['Access-Control-Allow-Headers'] = ['Origin', 'Content-Type', 'X-Auth-Token']
    return resp


@app.route('/api/v1/dataOperation/tests', methods=['GET', 'POST'])
def test_collection_service():
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        if request.args.get('formulationID'):
            formulation_id = request.args['formulationID']
            test_list = []
            test_rs = Formulation.query.get(formulation_id).test
            for test_r in test_rs:
                test_list.append({
                    'id': test_r.id,
                    'name': test_r.name,
                    'measure_type': test_r.measure_type,
                    'thickness': test_r.thickness,
                    'temperature_max': test_r.temperature_max,
                    'temperature_min': test_r.temperature_min,
                    'frequency_max': test_r.frequency_max,
                    'frequency_min': test_r.frequency_min,
                    'test_type': test_r.test_type,
                    'data_file_url': test_r.data_file_url,
                    'date': test_r.date.timestamp(),
                    'formulation_id': test_r.formulation_id,
                })
            resp = flask.Response(json.dumps({'status': 'success', 'test_list': test_list}))
    elif request.method == 'POST':
        if request.is_json:
            temperature, temperature_min, temperature_max = 0, 0, 0
            frequency, frequency_min, frequency_max = 0, 0, 0
            measure_type = request.json['measureType']
            date_ts = request.json.pop('date', datetime.now().timestamp())
            if measure_type == 'temperature':
                frequency_min = frequency_max = request.json['frequencyMin']
                temperature_min = request.json['temperatureMin']
                temperature_max = request.json['temperatureMax']
            elif measure_type == 'frequency':
                temperature_min = temperature_max = request.json['temperatureMin']
                frequency_min = request.json['frequencyMin']
                frequency_max = request.json['frequencyMax']
            test = Test(name=request.json['name'],
                        measure_type=measure_type,
                        thickness=request.json['thickness'],
                        temperature_max=temperature_max,
                        temperature_min=temperature_min,
                        frequency_max=frequency_max,
                        frequency_min=frequency_min,
                        test_type=request.json['testType'],
                        formulation_id=request.json['selectedFormulationID'],
                        date=datetime.fromtimestamp(date_ts))
            db.session.add(test)
            db.session.commit()
            resp = flask.Response(json.dumps({'status': 'success',
                                              'test_id': test.id,
                                              'test_name': test.name}))

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    resp.headers['Access-Control-Allow-Headers'] = ['Origin', 'Content-Type', 'X-Auth-Token']
    return resp


############################################################
# tests services end                                       #
############################################################

############################################################
# formulations services begin                              #
############################################################


@app.route('/api/v1/dataOperation/formulations', methods=['GET', 'POST'])
def formulation_collection_service():
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        formulations = []
        formulations_rs = Formulation.query.all()
        for formulation_r in formulations_rs:
            formulation_properties = []
            formulations_property_rs = formulation_r.formulation_property.all()
            for formulations_property_r in formulations_property_rs:
                formulation_properties.append({formulations_property_r.key: formulations_property_r.value})

            formulations.append({
                'id': formulation_r.id,
                'name': formulation_r.name,
                'date': formulation_r.date.timestamp(),
                'formulation_properties': formulation_properties
            })
        resp = flask.Response(json.dumps({'status': 'success', 'formulations': formulations}))
    elif request.method == 'POST':
        if request.is_json:
            req_json = request.json
            property_list, property_key_list = [], []
            name = req_json.pop('formulationName', 'formulation-%f' % datetime.now().timestamp())
            date_ts = req_json.pop('formulationDate', datetime.now().timestamp())
            property_key_list = [x for x in req_json if x.startswith('key-')]
            property_key_list.sort(key=lambda x: int(x.replace('key-', '')))
            for fpkey in property_key_list:
                key = req_json[fpkey]
                val = req_json['value-%s' % fpkey.split('-', maxsplit=1)[1]]
                property_list.append((key, val))
            # create new formulation in db
            formulation = Formulation(name=name, date=datetime.fromtimestamp(date_ts))
            db.session.add(formulation)
            db.session.commit()
            for fpkey, fpval in property_list:
                formulation.formulation_property.append(FormulationProperty(key=fpkey, value=fpval))
            db.session.commit()
            resp = flask.Response(json.dumps({'status': 'success',
                                              'new_formulation_id': formulation.id,
                                              'new_formulation_name': formulation.name}))

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS']
    resp.headers['Access-Control-Allow-Headers'] = ['Origin', 'Content-Type', 'X-Auth-Token']
    return resp


@app.route('/api/v1/dataOperation/formulations/<f_id>', methods=['PUT'])
def formulation_instance_service(f_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.is_json:
        p_json_list = request.json['properties']
        formulation = Formulation.query.get(f_id)
        formulation.formulation_property.delete()
        # fp_rs = Formulation.query.get(f_id).formulation_property
        # FormulationProperty.query.filter(FormulationProperty.formulation_id == f_id).delete()
        for p in p_json_list:
            formulation.formulation_property.append(FormulationProperty(
                key=p['keyName'],
                value=p['valueName']
            ))
        db.session.commit()
        p_list = []
        for p in formulation.formulation_property:
            p_list.append({p.key: p.value})
        resp = flask.Response(json.dumps({'status': 'success',
                                          'formulation_id': formulation.id,
                                          'formulation_properties': p_list}))
    return resp


@app.route('/api/v1/dataOperation/formulations/<int:f_id>/tests', methods=['GET', 'POST'])
def formulation_instance_test_collection_service(f_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        test_list = []
        test_rs = Formulation.query.get(f_id).test
        for test_r in test_rs:
            test_list.append({
                'id': test_r.id,
                'name': test_r.name,
                'measure_type': test_r.measure_type,
                'thickness': test_r.thickness,
                'temperature_max': test_r.temperature_max,
                'temperature_min': test_r.temperature_min,
                'frequency_max': test_r.frequency_max,
                'frequency_min': test_r.frequency_min,
                'test_type': test_r.test_type,
                'data_file_url': test_r.data_file_url,
                'date': test_r.date.timestamp(),
                'formulation_id': test_r.formulation_id,
            })
        resp = flask.Response(json.dumps({
            'status': 'success',
            'test_list': test_list,
            'formulation_id': f_id,
        }))
    return resp

############################################################
# formulations services begin                              #
############################################################
