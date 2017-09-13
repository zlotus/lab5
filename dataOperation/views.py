import flask
import json
import os
from shutil import rmtree
from flask import request
from app import app
from app import db
from dataOperation.utils import allowed_file, set_debug_response_header
from config import UPLOAD_FOLDER
from dataOperation.models import Formulation, FormulationProperty, Test, TestData, TestAttachment
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import func
from pprint import pprint


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

    return set_debug_response_header(resp)


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

    return set_debug_response_header(resp)


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
    if test_id <= 0:
        return set_debug_response_header(resp)

    if request.method == 'GET':
        formulation_id = Test.query.get(test_id).formulation_id
        test_data = {
            'e_prime': [],
            'tan_delta': []
        }
        td_rs = Test.query.get(test_id).test_data.order_by(TestData.x_value)
        for td_r in td_rs:
            if td_r.data_type == "E'":
                test_data['e_prime'].append({'x': td_r.x_value, 'y': td_r.y_value})
            elif td_r.data_type == 'Tan Delta':
                test_data['tan_delta'].append({'x': td_r.x_value, 'y': td_r.y_value})
        resp = flask.Response(json.dumps({'status': 'success',
                                          'formulation_id': formulation_id,
                                          'test_id': test_id,
                                          'test_data': test_data,
                                          'test': test_data}))
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

    return set_debug_response_header(resp)


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

    return set_debug_response_header(resp)


@app.route('/api/v1/dataOperation/tests/<int:test_id>', methods=['DELETE'])
def test_instance_service(test_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'DELETE':
        formulation_id = request.json['formulationID']
        Test.query.filter(Test.id == test_id).delete()
        TestData.query.filter(TestData.test_id == test_id).delete()
        TestAttachment.query.filter(TestAttachment.test_id == test_id).delete()

        try:
            dirpath = os.path.join(UPLOAD_FOLDER, str(test_id))
            rmtree(dirpath)
            db.session.commit()
            resp = flask.Response(
                json.dumps({'status': 'success', 'test_id': test_id, 'formulation_id': formulation_id}))
        except OSError:
            resp = flask.Response(json.dumps({'status': 'failed', 'test_id': test_id}))

    return set_debug_response_header(resp)


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

    return set_debug_response_header(resp)


@app.route('/api/v1/dataOperation/formulations/<f_id>', methods=['PUT', 'DELETE'])
def formulation_instance_service(f_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'PUT':
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
    elif request.method == 'DELETE':
        formulation = Formulation.query.get(f_id)
        test_count = formulation.test.count()
        if test_count > 0:
            resp = flask.Response(json.dumps({'status': 'failed',
                                              'error': 'the tests count of formulation id %d is not 0, '
                                                       'delete tests first'}))
        else:
            Formulation.query.filter(Formulation.id == f_id).delete()
            db.session.commit()
    return set_debug_response_header(resp)


@app.route('/api/v1/dataOperation/formulations/<int:f_id>/tests', methods=['GET'])
def formulation_instance_test_collection_service(f_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        test_list = []
        test_rs = Formulation.query.get(f_id).test
        for test_r in test_rs:
            attachment_list = []
            at_rs = test_r.test_attachment
            for at_r in at_rs:
                attachment_list.append({'attachment_name': at_r.name, 'attachment_url': at_r.attachment_url})
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
                'attachment_url': attachment_list
            })
        resp = flask.Response(json.dumps({
            'status': 'success',
            'test_list': test_list,
            'formulation_id': f_id,
        }))
    return set_debug_response_header(resp)


# x: temperature, y: frequency, z: tan delta
@app.route('/api/v1/dataOperation/formulations/<int:f_id>/data', methods=['GET'])
def formulation_instance_data_collection_service(f_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        test_rs = Formulation.query.get(f_id).test
        lines = []
        for test_r in test_rs:
            td_rs = test_r.test_data.order_by(TestData.x_value)
            xt, yt, zt = [], [], []
            xe, ye, ze = [], [], []
            if test_r.measure_type == 'temperature':
                for td_r in td_rs:
                    if td_r.data_type == 'Tan Delta':
                        xt.append(td_r.x_value)
                        yt.append(test_r.frequency_min)
                        zt.append(td_r.y_value)
                    else:
                        xe.append(td_r.x_value)
                        ye.append(test_r.frequency_min)
                        ze.append(td_r.y_value)
            else:
                for td_r in td_rs:
                    if td_r.data_type == 'Tan Delta':
                        xt.append(test_r.temperature_min)
                        yt.append(td_r.x_value)
                        zt.append(td_r.y_value)
                    else:
                        xe.append(test_r.temperature_min)
                        ye.append(td_r.x_value)
                        ze.append(td_r.y_value)
            line = {'xt': xt, 'yt': yt, 'zt': zt, 'xe': xe, 'ye': ye, 'ze': ze, 'name': test_r.name, 'id': test_r.id}
            lines.append(line)
        resp = flask.Response(json.dumps({
            'status': 'success',
            'lines': lines,
            'formulation_id': f_id,
        }))
    return set_debug_response_header(resp)


############################################################
# formulations services begin                              #
############################################################

############################################################
# global services begin                                    #
############################################################


@app.route('/api/v1/dataOperation/data', methods=['GET'])
def data_collection_service():
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.method == 'GET':
        temperature_min = request.args.get('temperatureMin', type=float)
        temperature_max = request.args.get('temperatureMax', type=float)
        frequency_min = request.args.get('frequencyMin', type=float)
        frequency_max = request.args.get('frequencyMax', type=float)
        tan_delta_min = request.args.get('tanDeltaMin', type=float)
        tan_delta_max = request.args.get('tanDeltaMax', type=float)
        e_prime_min = request.args.get('ePrimeMin', type=float)
        e_prime_max = request.args.get('ePrimeMax', type=float)
        fm_list_query_results = []
        # [
        #   {
        #       'formulation_id': 1,
        #       'formulation_name': 'f1',
        #       'formulation_date': '2017-07-20',
        #       'formulation_properties': [
        #           'key': 'value'
        #           ...
        #       ],
        #       'fm_query_results': [
        #           {
        #               'test_id': 1,
        #               'name': 't1'
        #               ...
        #               'e_prime_data': [
        #                   {'x': 1, 'y': 2},
        #                   ...
        #               ],
        #               'tan_delta_data': [
        #                   {'x': 1, 'y': 2},
        #                   ...
        #               ]
        #           },
        #       ]
        #   },
        #   ...
        # ]
        for fm_r in Formulation.query.all():
            f_dict = {
                'id': fm_r.id,
                'name': fm_r.name,
                'date': fm_r.date.strftime('%Y-%m-%d %H:%M:%S'),
                'formulation_properties': [{p.key: p.value} for p in fm_r.formulation_property],
                'fm_query_results': []
            }

            for test_r in fm_r.test:
                if test_r.measure_type == 'temperature' and frequency_min <= test_r.frequency_min <= frequency_max:
                    e_prime_data_rs = TestData.query.filter(
                        (TestData.test_id == test_r.id) &
                        (TestData.data_type == 'E\'') &
                        (TestData.x_value >= temperature_min) & (TestData.x_value <= temperature_max) &
                        (TestData.y_value >= e_prime_min) & (TestData.y_value <= e_prime_max)
                    ).order_by(TestData.x_value)
                    tan_delta_data_rs = TestData.query.filter(
                        (TestData.test_id == test_r.id) &
                        (TestData.data_type == 'Tan Delta') &
                        (TestData.x_value >= temperature_min) & (TestData.x_value <= temperature_max) &
                        (TestData.y_value >= tan_delta_min) & (TestData.y_value <= tan_delta_max)
                    ).order_by(TestData.x_value)
                    if e_prime_data_rs.count() > 0 or tan_delta_data_rs.count() > 0:
                        test_query_result = {
                            'id': test_r.id,
                            'name': test_r.name,
                            'measure_type': test_r.measure_type,
                            'thickness': test_r.thickness,
                            'temperature_min': test_r.temperature_min,
                            'temperature_max': test_r.temperature_max,
                            'frequency_min': test_r.frequency_min,
                            'frequency_max': test_r.frequency_max,
                            'test_type': test_r.test_type,
                            'date': test_r.date.strftime('%Y-%m-%d %H:%M:%S'),
                            'e_prime_data': [],
                            'tan_delta_data': [],
                        }
                        for data_r in e_prime_data_rs:
                            test_query_result['e_prime_data'].append({'x': data_r.x_value, 'y': data_r.y_value})
                        for data_r in tan_delta_data_rs:
                            test_query_result['tan_delta_data'].append({'x': data_r.x_value, 'y': data_r.y_value})
                        f_dict['fm_query_results'].append(test_query_result)
                elif test_r.measure_type == 'frequency' and temperature_min <= test_r.temperature_min <= temperature_max:
                    e_prime_data_rs = TestData.query.filter(
                        (TestData.test_id == test_r.id) &
                        (TestData.data_type == 'E\'') &
                        (TestData.x_value >= frequency_min) & (TestData.x_value <= frequency_max) &
                        (TestData.y_value >= e_prime_min) & (TestData.y_value <= e_prime_max)
                    ).order_by(TestData.x_value)
                    tan_delta_data_rs = TestData.query.filter(
                        (TestData.test_id == test_r.id) &
                        (TestData.data_type == 'Tan Delta') &
                        (TestData.x_value >= frequency_min) & (TestData.x_value <= frequency_max) &
                        (TestData.y_value >= tan_delta_min) & (TestData.y_value <= tan_delta_max)
                    ).order_by(TestData.x_value)
                    if e_prime_data_rs.count() > 0 or tan_delta_data_rs.count() > 0:
                        test_query_result = {
                            'id': test_r.id,
                            'name': test_r.name,
                            'measure_type': test_r.measure_type,
                            'thickness': test_r.thickness,
                            'temperature_min': test_r.temperature_min,
                            'temperature_max': test_r.temperature_max,
                            'frequency_min': test_r.frequency_min,
                            'frequency_max': test_r.frequency_max,
                            'test_type': test_r.test_type,
                            'date': test_r.date.strftime('%Y-%m-%d %H:%M:%S'),
                            'e_prime_data': [],
                            'tan_delta_data': [],
                        }
                        for data_r in e_prime_data_rs:
                            test_query_result['e_prime_data'].append({'x': data_r.x_value, 'y': data_r.y_value})
                        for data_r in tan_delta_data_rs:
                            test_query_result['tan_delta_data'].append({'x': data_r.x_value, 'y': data_r.y_value})
                        f_dict['fm_query_results'].append(test_query_result)
            if len(f_dict['fm_query_results']) > 0:
                fm_list_query_results.append(f_dict)
        pprint(fm_list_query_results)
        resp = flask.Response(json.dumps({'status': 'success', 'query_result': fm_list_query_results}))

    return set_debug_response_header(resp)

############################################################
# global services begin                                    #
############################################################
