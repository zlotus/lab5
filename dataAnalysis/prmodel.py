from dataOperation.models import Formulation, TestData
from numpy import array
from sklearn.preprocessing import StandardScaler
import os
from config import MODEL_FOLDER
from keras.layers import Dense
from keras.models import Sequential, load_model
from keras.callbacks import LambdaCallback
import json
import numpy as np
from datetime import datetime
from redis import Redis
from math import ceil, floor

r = Redis(host='127.0.0.1')


class FormulationDataModel:
    def __init__(self, f_id, model_name='', hidden_layers=9, activation='selu'):
        self.f_id = f_id
        self.fit_history = None
        self.model_dir = os.path.join(MODEL_FOLDER, str(f_id), 'model')
        self.log_dir = os.path.join(MODEL_FOLDER, str(f_id), 'log')
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        # init sequential model
        if model_name != '':
            self.model = load_model(os.path.join(self.model_dir, str(model_name)))
        else:
            self.model = Sequential()
            self.model.add(Dense(64, input_dim=2, activation=activation, kernel_initializer='random_normal'))
            for i in range(hidden_layers):
                self.model.add(Dense(64, activation=activation, kernel_initializer='random_normal'))
            self.model.add(Dense(1, activation=activation, kernel_initializer='random_normal'))
            self.model.compile(loss='mse', optimizer='nadam')

    def get_formulation_training_data(self):
        # prepare data lines to plot
        data_lines = self.get_formulation_line_data()
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
        return X, y, data_traces

    def fit_model(self, logging_uuid, model=None, epochs=1000, batch_size=10):
        if model is not None:
            self.model = model
        X, y, _ = self.get_formulation_training_data()
        scaler = StandardScaler().fit(X)
        lcb = LambdaCallback(
            on_epoch_end=
            lambda epoch, logs:
            r.set(logging_uuid, json.dumps({'model_state': 'training',
                                            'epoch': epoch,
                                            'epochs': epochs,
                                            'loss': logs['loss']})),
            on_train_end=
            lambda logs:
            r.set(logging_uuid, json.dumps({'model_state': 'training',
                                            'epoch': epochs,
                                            'epochs': epochs})),
        )
        self.fit_history = self.model.fit(scaler.transform(X), y,
                                          epochs=epochs,
                                          batch_size=batch_size,
                                          verbose=0,
                                          callbacks=[lcb])
        return self.model, self.fit_history

    def get_formulation_predict_data(self, model=None, grid_step=3):
        if model is not None:
            self.model = model
        # prepare data lines to plot
        X, y, data_traces = self.get_formulation_training_data()
        # train model to fit data lines
        scaler = StandardScaler().fit(X)
        # prepare mesh grid to plot
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
        # predict z using model just trained
        grid_z_list = []
        for grid_line in grid_xy_list:
            grid_z_list.append(self.model.predict(scaler.transform(grid_line)).reshape((-1)))
        # prepare grid to plot
        grid_traces = []
        for grid_line_index, grid_line in enumerate(grid_xy_list):
            grid_traces.append({'x': grid_line[:, 0].tolist(),
                                'y': grid_line[:, 1].tolist(),
                                'z': grid_z_list[grid_line_index].tolist()})
        return data_traces, grid_traces

    def get_saved_model_list(self):
        saved_model_list = []
        for entry in os.scandir(self.model_dir):
            if entry.is_file(follow_symlinks=False):
                saved_model_list.append({'model_name': entry.name})

    def save_model(self, model_name=str(datetime.now().timestamp()), model=None):
        if model is not None:
            self.model = model
        self.model.save(os.path.join(self.model_dir, str(model_name)))

    def get_formulation_line_data(self, data_type="Tan Delta"):
        lines = []

        test_rs = Formulation.query.get(self.f_id).test
        for test_r in test_rs:
            line = []
            td_rs = TestData.query.filter(
                (TestData.test_id == test_r.id) & (TestData.data_type == data_type)
            ).order_by(TestData.x_value)

            if test_r.measure_type == 'temperature':
                for td_r in td_rs:
                    if td_r.data_type == data_type:
                        line.append([td_r.x_value, test_r.frequency_min, td_r.y_value])
            else:
                for td_r in td_rs:
                    if td_r.data_type == data_type:
                        line.append([test_r.temperature_min, td_r.x_value, td_r.y_value])
            lines.append(line)
        return lines
