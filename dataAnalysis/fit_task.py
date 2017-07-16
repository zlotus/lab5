from dataAnalysis.prmodel import FormulationDataModel
from math import ceil, floor
import numpy as np
import json
from app import celery
from redis import Redis
from datetime import datetime

r = Redis(host='127.0.0.1')


@celery.task
def fit_model_task(f_id, training_uuid, logging_uuid, epochs=100):
    fdm = FormulationDataModel(f_id)
    model, fit_history = fdm.fit_model(logging_uuid, epochs=epochs)
    data_traces, grid_traces = fdm.get_formulation_predict_data()
    # save model with a format name like 2017-07-12_20-38-39_loss-0.0118556629749.hdf5
    model_name = '%s_loss-%s.hdf5' % (datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), str(fit_history.history['loss'][-1]))
    fdm.save_model(model=model, model_name=model_name)

    result = json.dumps({'status': 'success',
                         'formulation_id': f_id,
                         'data_traces': data_traces,
                         'grid_traces': grid_traces,
                         'model_name': model_name})
    r.set(training_uuid, result)
    r.set(logging_uuid, json.dumps({'model_state': 'trained'}))
