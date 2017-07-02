from dataOperation.models import Formulation, TestData
from numpy import array
from sklearn.preprocessing import StandardScaler
import os
from config import MODEL_FOLDER
from keras.layers import Dense
from keras.models import Sequential
from keras.callbacks import LambdaCallback
import json
from redis import Redis

r = Redis(host='127.0.0.1')


class FormulationDataModel:
    def __init__(self, f_id):
        self.f_id = f_id
        self.model = None
        self.fit_history = None
        self.scaler = None
        self.model_dir = os.path.join(MODEL_FOLDER, str(f_id), 'model')
        self.log_dir = os.path.join(MODEL_FOLDER, str(f_id), 'log')
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

    def get_formulation_train_data(self, data_type="Tan Delta"):
        input_m = []
        output_m = []

        test_rs = Formulation.query.get(self.f_id).test
        for test_r in test_rs:
            td_rs = TestData.query.filter(
                (TestData.test_id == test_r.id) & (TestData.data_type == data_type)
            ).order_by(TestData.x_value)

            if test_r.measure_type == 'temperature':
                for td_r in td_rs:
                    if td_r.data_type == data_type:
                        input_m.append([td_r.x_value, test_r.frequency_min])
                        output_m.append(td_r.y_value)
            else:
                for td_r in td_rs:
                    if td_r.data_type == data_type:
                        input_m.append([test_r.temperature_min, td_r.x_value])
                        output_m.append(td_r.y_value)
        return array(input_m), array(output_m)

    def get_model(self, hidden_layers=9, activation='selu'):
        model = Sequential()
        model.add(Dense(64, input_dim=2, activation='selu', kernel_initializer='random_normal'))
        for i in range(hidden_layers):
            model.add(Dense(64, activation=activation, kernel_initializer='random_normal'))
        model.add(Dense(1, activation='selu', kernel_initializer='random_normal'))
        model.compile(loss='mse', optimizer='nadam')
        self.model = model
        return model

    def fit_model(self, model, X, y, logging_uuid, epochs=1000, batch_size=10):
        scaler = StandardScaler().fit(X)
        lcb = LambdaCallback(
            on_epoch_end=
            lambda epoch, logs:
            r.set(logging_uuid, json.dumps({'model_state':'training',
                                            'epoch': epoch,
                                            'epochs': epochs,
                                            'loss': logs['loss']})),
            on_train_end=
            lambda logs:
            r.set(logging_uuid, json.dumps({'model_state':'training',
                                            'epoch': epochs,
                                            'epochs': epochs})),
        )
        fit_history = model.fit(scaler.transform(X), y,
                                epochs=epochs,
                                batch_size=batch_size,
                                verbose=0,
                                callbacks=[lcb])
        self.model = model
        self.fit_history = fit_history
        self.scaler = scaler
        return model, fit_history, scaler

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
