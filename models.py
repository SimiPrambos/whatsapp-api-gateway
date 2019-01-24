from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ApiConfig(db.Model):
    __tablename__ = 'apiconfig'
    id = db.Column(db.Integer, primary_key=True)
    client = db.Column(db.String(100), unique=True) 
    key = db.Column(db.String(200))
    webhook = db.Column(db.Boolean)
    webhook_url = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return self.client