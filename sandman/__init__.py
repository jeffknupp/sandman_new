from __future__ import absolute_import

from flask import Flask, jsonify, g
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
    ServiceUnavailableException,
    InvalidAPIUsage
    )
from sandman.models import db, Model
from sandman.content_negotiation import (
        _get_acceptable_response_type,
        JSON,
        HTML,
        )
from sandman.admin import admin

app = Flask(__name__)
app.register_blueprint(admin, url_prefix='/admin')
with app.app_context():
    g.class_registery = {}

__version__ = '0.0.1'


def init_app(app, models):
    """Initialize and register error handlers."""

    # pylint: disable=unused-variable

    register(models)


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

@app.errorhandler(InvalidAPIUsage)
def handle_exception(error):
    """Return a response with the appropriate status code, message, and content
    type when an ``InvalidAPIUsage`` exception is raised."""
    try:
        if _get_acceptable_response_type() == JSON:
            response = jsonify(error.to_dict())
            response.status_code = error.code
            return response
        else:
            return error.abort()
    except InvalidAPIUsage as _:
        # In addition to the original exception, we don't support the content
        # type in the request's 'Accept' header, which is a more important
        # error, so return that instead of what was originally raised.
        response = jsonify(error.to_dict())
        response.status_code = 415
        return response

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
            cls.__app__ = app
            view_func = cls.as_view(
                cls.__tablename__)
            app.add_url_rule(
                '/' + cls.endpoint(),
                view_func=view_func)
            app.add_url_rule(
                '/{resource}/<resource_id>'.format(
                    resource=cls.endpoint()),
                view_func=view_func, methods=[
                    'GET',
                    'PUT',
                    'DELETE',
                    'PATCH',
                    'OPTIONS'])
