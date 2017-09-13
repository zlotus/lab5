from app import db


class Formulation(db.Model):
    __tablename__ = 'Formulation'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63))
    date = db.Column(db.DATETIME)
    model_name = db.Column(db.String(128))
    memo = db.Column(db.String(128))
    
    formulation_property = db.relationship('FormulationProperty', backref='formulation', lazy='dynamic')
    test = db.relationship('Test', backref='formulation', lazy='dynamic')
    formulation_data_grid = db.relationship('FormulationDataGrid', backref='formulation', lazy='dynamic')

    def __repr__(self):
        return '<Fomulation %r>' % self.name


class FormulationProperty(db.Model):
    __tablename__ = 'FormulationProperty'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(63))
    value = db.Column(db.String(63))
    memo = db.Column(db.String(128))
    
    formulation_id = db.Column(db.Integer, db.ForeignKey('Formulation.id'))

    def __repr__(self):
        return '<FormulationProperty %r: %r>' % (self.key, self.value)


class FormulationDataGrid(db.Model):
    __tablename__ = 'FormulationDataGrid'
    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.Integer)
    x_value = db.Column(db.Float)
    y_value = db.Column(db.Float)
    z_value = db.Column(db.Float)
    formulation_id = db.Column(db.Integer, db.ForeignKey('Formulation.id'))

    def __repr__(self):
        return '<FormulationDataGrid %d: (%f, %f, %f)>' % (self.formulation_id, self.x_value, self.y_value, self.z_value)


class Test(db.Model):
    __tablename__ = 'Test'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63))
    measure_type = db.Column(db.String(15))
    thickness = db.Column(db.Float)
    temperature_min = db.Column(db.Float)
    temperature_max = db.Column(db.Float)
    frequency_min = db.Column(db.Float)
    frequency_max = db.Column(db.Float)
    test_type = db.Column(db.String(15))
    data_file_url = db.Column(db.String(255))
    date = db.Column(db.DATETIME)
    memo = db.Column(db.String(127))
    
    formulation_id = db.Column(db.Integer, db.ForeignKey('Formulation.id'))
    
    test_data = db.relationship('TestData', backref='test', lazy='dynamic')
    test_attachment = db.relationship('TestAttachment', backref='test', lazy='dynamic')

    def __repr__(self):
        return '<Test %d:%r>' % (self.formulation_id, self.name)


class TestData(db.Model):
    __tablename__ = 'TestData'
    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer)
    x_value = db.Column(db.Float)
    y_value = db.Column(db.Float)
    data_type = db.Column(db.String(15))
    memo = db.Column(db.String(127))
    test_id = db.Column(db.Integer, db.ForeignKey('Test.id'))

    def __repr__(self):
        return '<TestData (%f, %f)>' % (self.x_value, self.y_value)


class TestAttachment(db.Model):
    __tablename__ = 'TestAttachment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63))
    attachment_url = db.Column(db.String(255))
    memo = db.Column(db.String(127))
    test_id = db.Column(db.Integer, db.ForeignKey('Test.id'))

    def __repr__(self):
        return '<TestAttachment %r>' % self.name
