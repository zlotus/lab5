import flask
from flask import request
import json
import numpy as np
from dataAnalysis.utils import set_debug_response_header
from app import app
from dataAnalysis.prmodel import FormulationDataModel
from math import ceil, floor
from datetime import datetime
from dataAnalysis.fit_task import fit_model_task
import uuid
import redis
from dataOperation.models import Formulation, TestData

r = redis.Redis()


@app.route('/api/v1/dataAnalysis/formulations/<int:f_id>/models', methods=['GET'])
def formulation_instance_model_collection_train_analysis_service(f_id):
    resp = flask.Response(json.dumps({'status': 'failed'}))
    if request.args.get('action') == 'start':
        training_uuid = str(uuid.uuid1()).replace('-', '')[:8]
        logging_uuid = str(uuid.uuid1()).replace('-', '')[:8]
        fit_model_task.delay(training_uuid, logging_uuid, f_id, epochs=int(request.args.get('epochs')))
        resp = flask.Response(json.dumps({'status': 'success',
                                          'formulation_id': f_id,
                                          'training_uuid': training_uuid,
                                          'logging_uuid': logging_uuid}))
    elif request.args.get('action') == 'getPlotData':
        resp = flask.Response(r.get(request.args.get('redisTrainingTaskID')))
    else:
        fdm = FormulationDataModel(f_id)
        saved_model_list = fdm.get_saved_model_list()
        if len(saved_model_list) > 0:
            resp = flask.Response({'saved_model_list': saved_model_list})
    return set_debug_response_header(resp)


@app.route('/api/v1/dataAnalysis/formulations/<int:f_id>/logs', methods=['GET'])
def formulation_instance_log_collection_analysis_service(f_id):
    resp = flask.Response(r.get(request.args.get('redisLoggingTaskID')))
    return set_debug_response_header(resp)


@app.route('/api/v1/dataAnalysis/formulations/<int:f_id>/models/<string:model_name>/', methods=['GET'])
def formulation_instance_model_instance_analysis_service(f_id, model_name):
    fdm = FormulationDataModel(f_id, model_name=model_name)
    data_traces, grid_traces = fdm.get_formulation_predict_data()
    resp = flask.Response(json.dumps({'status': 'success',
                                      'formulation_id': f_id,
                                      'data_traces': data_traces,
                                      'grid_traces': grid_traces,
                                      'model_name': model_name}))
    return set_debug_response_header(resp)


@app.route('/api/v1/dataAnalysis/formulations/', methods=['GET'])
def formulation_collection_analysis_service():
    formulations = []
    formulations_rs = Formulation.query.all()
    for formulation_r in formulations_rs:
        formulation_properties = []
        formulations_property_rs = formulation_r.formulation_property.all()
        test_count = formulation_r.test.count()
        for formulations_property_r in formulations_property_rs:
            formulation_properties.append({formulations_property_r.key: formulations_property_r.value})

        formulations.append({
            'id': formulation_r.id,
            'name': formulation_r.name,
            'date': formulation_r.date.timestamp(),
            'formulation_properties': formulation_properties,
            'test_count': test_count
        })
    resp = flask.Response(json.dumps({'status': 'success', 'formulation_list': formulations}))
    return resp


# x: temperature, y: frequency, z: tan delta
@app.route('/api/v1/dataAnalysis/formulations/<int:f_id>/data', methods=['GET'])
def formulation_instance_data_collection_analysis_service(f_id):
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
