"""Run server"""
from sqlalchemy.ext.automap import automap_base
from sandman import app, reflect_all
from sandman.models import db
import models
import os
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite+pysqlite:///existing.sqlite3'
app.secret_key = 's3cr3t'
db.init_app(app)
reflect_all()
app.run(host='0.0.0.0', debug=True)
