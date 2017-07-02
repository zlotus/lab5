from dataAnalysis.prmodel import FormulationDataModel
from math import ceil, floor
import numpy as np
import json
from app import celery
from redis import Redis

r = Redis(host='127.0.0.1')


@celery.task
def fit_model_task(training_uuid, logging_uuid, f_id, epochs=100):
    fdm = FormulationDataModel(f_id)
    # resp = flask.Response(json.dumps({'status': 'failed'}))
    # prepare data lines to plot
    data_lines = fdm.get_formulation_line_data()
    data_array_list = []
    data_traces = []
    for data_line in data_lines:
        data_line_array = np.array(data_line)
        data_array_list.append(data_line_array)
        data_traces.append({'x': data_line_array[:, 0].tolist(),
                            'y': data_line_array[:, 1].tolist(),
                            'z': data_line_array[:, 2].tolist()})
    # prepare numpy arrays to fit
    data_array = np.concatenate(data_array_list)
    X = data_array[:, :2]
    y = data_array[:, 2]
    # train model to fit data lines
    model = fdm.get_model()
    model, fit_history, scaler = fdm.fit_model(model, X, y, logging_uuid, epochs=epochs)
    # prepare mesh grid to plot
    grid_step = 3
    max_t, max_f = np.amax(X, axis=0)
    min_t, min_f = np.amin(X, axis=0)
    xv, yv = np.meshgrid(np.arange(floor(min_t), ceil(max_t), grid_step),
                         np.arange(floor(min_f), ceil(max_f), grid_step),
                         indexing='ij')
    xv = xv.reshape((xv.shape[0], xv.shape[1], -1))
    yv = yv.reshape((yv.shape[0], yv.shape[1], -1))
    grid = np.concatenate((xv, yv), axis=2)
    grid_xy_list = []
    # x fixed lines
    for i in range(grid.shape[0]):
        grid_xy_list.append(grid[i, :, :])
    # y fixed lines
    for j in range(grid.shape[1]):
        grid_xy_list.append(grid[:, j, :])
    # predict z by model
    grid_z_list = []
    for grid_line in grid_xy_list:
        grid_z_list.append(model.predict(scaler.transform(grid_line)).reshape((-1)))
    # prepare grid to plot
    grid_traces = []
    for grid_line_index, grid_line in enumerate(grid_xy_list):
        grid_traces.append({'x': grid_line[:, 0].tolist(),
                            'y': grid_line[:, 1].tolist(),
                            'z': grid_z_list[grid_line_index].tolist()})

    result = json.dumps({'status': 'success',
                         'formulation_id': f_id,
                         'data_traces': data_traces,
                         'grid_traces': grid_traces})
    r.set(training_uuid, result)
    r.set(logging_uuid, json.dumps({'model_state': 'trained'}))

    # resp = flask.Response(json.dumps({'status': 'success',
    #                                   'formulation_id': f_id,
    #                                   'data_traces': data_traces,
    #                                   'grid_traces': grid_traces}))
    # return resp
