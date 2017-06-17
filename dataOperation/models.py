from app import db


class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(64))
    memo = db.Column(db.String(128))
    
    user_right = db.relationship('UserRight', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.name


class UserRight(db.Model):
    __tablename__ = 'UserRight'
    id = db.Column(db.Integer, primary_key=True)
    right_code = db.Column(db.String(128), index=True)
    right_description = db.Column(db.String(128))
    memo = db.Column(db.String(128))
    
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))

    def __repr__(self):
        return '<UserRight %r>' % self.right_code


class Formulation(db.Model):
    __tablename__ = 'Formulation'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    date = db.Column(db.DATETIME)
    memo = db.Column(db.String(128))
    
    formulation_property = db.relationship('FormulationProperty', backref='formulation', lazy='dynamic')
    test = db.relationship('Test', backref='formulation', lazy='dynamic')

    def __repr__(self):
        return '<Fomulation %r>' % self.name


class FormulationProperty(db.Model):
    __tablename__ = 'FormulationProperty'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64))
    value = db.Column(db.String(64))
    memo = db.Column(db.String(128))
    
    formulation_id = db.Column(db.Integer, db.ForeignKey('Formulation.id'))

    def __repr__(self):
        return '<FormulationProperty %r: %r>' % (self.key, self.value)


class Test(db.Model):
    __tablename__ = 'Test'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    measure_type = db.Column(db.String(16))
    thickness = db.Column(db.Float)
    temperature_min = db.Column(db.Float)
    temperature_max = db.Column(db.Float)
    frequency_min = db.Column(db.Float)
    frequency_max = db.Column(db.Float)
    test_type = db.Column(db.String(16))
    data_file_url = db.Column(db.String(256))
    date = db.Column(db.DATETIME)
    memo = db.Column(db.String(128))
    
    formulation_id = db.Column(db.Integer, db.ForeignKey('Formulation.id'))
    
    test_data = db.relationship('TestData', backref='test', lazy='dynamic')
    test_attachment = db.relationship('TestAttachment', backref='test', lazy='dynamic')

    def __repr__(self):
        return '<Test %r>' % self.name


class TestData(db.Model):
    __tablename__ = 'TestData'
    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer)
    x_value = db.Column(db.Float)
    y_value = db.Column(db.Float)
    data_type = db.Column(db.String(16))
    memo = db.Column(db.String(128))
    test_id = db.Column(db.Integer, db.ForeignKey('Test.id'))

    def __repr__(self):
        return '<TestData %r>' % self.name


class TestAttachment(db.Model):
    __tablename__ = 'TestAttachment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    attachment_url = db.Column(db.String(256))
    date = db.Column(db.DATETIME)
    memo = db.Column(db.String(128))
    test_id = db.Column(db.Integer, db.ForeignKey('Test.id'))

    def __repr__(self):
        return '<TestAttachment %r>' % self.name
