from __future__ import absolute_import

from flask import Flask, jsonify
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import Table

from sandman.exception import (
    BadRequestException,
    ForbiddenException,
    NotAcceptableException,
    NotFoundException,
    ConflictException,
    ServerErrorException,
    NotImplementedException,
    ServiceUnavailableException)
from sandman.models import db, Model

app = Flask(__name__)


__version__ = '0.0.1'


def init_app(app, models):
    """Initialize and register error handlers."""

    # pylint: disable=unused-variable

    @app.errorhandler(BadRequestException)
    @app.errorhandler(ForbiddenException)
    @app.errorhandler(NotAcceptableException)
    @app.errorhandler(NotFoundException)
    @app.errorhandler(ConflictException)
    @app.errorhandler(ServerErrorException)
    @app.errorhandler(NotImplementedException)
    @app.errorhandler(ServiceUnavailableException)
    def handle_application_error(error):
        """Handler used to send JSON error messages rather than default
        HTML ones."""
        response = jsonify(error.to_dict())
        response.status_code = error.code
        return response

    register(models)

def add_pk(db, cls):
    """Return a class deriving from our Model class as well as the SQLAlchemy
    model.

    :param `sqlalchemy.schema.Table` table: table to create primary key for
    :param  table: table to create primary key for

    """
    db.metadata.reflect(bind=db.engine)
    table = db.metadata.tables[cls.__tablename__]
    cls_dict = {'__tablename__': cls.__tablename__}
    if not table.primary_key:
        for column in table.columns:
            column.primary_key = True
        Table(cls.__name__, db.metadata, *table.columns, extend_existing=True)
        cls_dict['__table__'] = table

    return type(str(cls.__name__), (db.Model, ), cls_dict)


def reflect_all():
    with app.app_context():

        db.metadata.reflect(bind=db.engine)
        for name, table in db.metadata.tables.items():
            new_cls = type(str(name), (Model,), {'__tablename__': str(name), '__table__': table})
            register([new_cls])


def register(cls_list):
    """Register a class to be given a REST API."""
    with app.app_context():
        Base = automap_base()
        Base.prepare(db.engine, reflect=True)
        for cls in cls_list:
            try:
                sqlalchemy_class = getattr(Base.classes, cls.__tablename__)
            except AttributeError:
                # Not mapped during reflection, likely due to missing primary
                # key
                sqlalchemy_class = add_pk(db, cls)
            cls.__model__ = sqlalchemy_class
            cls.__db__ = db
            view_func = cls.as_view(
                cls.__tablename__)
            app.add_url_rule(
                '/' + cls.__tablename__.lower(),
                view_func=view_func)
            app.add_url_rule(
                '/{resource}/<resource_id>'.format(
                    resource=cls.__tablename__.lower()),
                view_func=view_func, methods=[
                    'GET',
                    'PUT',
                    'DELETE',
                    'PATCH',
                    'OPTIONS'])
