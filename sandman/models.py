import datetime
from functools import wraps

from flask import jsonify, request, make_response
from flask.views import MethodView
from flask.ext.sqlalchemy import SQLAlchemy

from sandman.exception import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    )

db = SQLAlchemy()

def verify_fields(function):
    """A decorator to automatically verify all required JSON fields
    have been sent."""
    @wraps(function)
    def decorated(instance, *args, **kwargs):
        """The decorator function."""
        data = request.get_json(force=True, silent=True)
        print data
        if not data:
            raise BadRequestException("No data received from request")
        for required in instance.__model__.__table__.columns:
            if required.name in (
                    instance.__model__.__table__.primary_key.columns):
                continue
            if required.name not in data:
                raise ForbiddenException('{} required'.format(required))
        return function(instance, *args, **kwargs)

    return decorated


class Model(MethodView):
    """Base class for all resources."""

    __model__ = None
    __db__ = None

    def get(self, resource_id=None):
        """Return response to HTTP GET request."""
        if resource_id is None:
            return self._all_resources()
        else:
            resource = self._resource(resource_id)
            if not resource:
                raise NotFoundException
            return jsonify(self.to_dict(resource))

    def _all_resources(self):
        """Return all resources of this type as a JSON list."""
        if not 'page' in request.args:
            resources = self.__db__.session.query(self.__model__).all()
        else:
            resources = self.__model__.query.paginate(
                int(request.args['page'])).items
        return jsonify(
            {'resources': [self.to_dict(resource) for resource in resources]})

    @verify_fields
    def post(self):
        """Return response to HTTP POST request."""
        # pylint: disable=unused-argument
        resource = self.__model__.query.filter_by(**request.json).first()
        # resource already exists; don't create it again
        if resource:
            raise BadRequestException('resource already exists')
        resource = self.__model__(  # pylint: disable=not-callable
            **request.json)
        self.__db__.session.add(resource)
        self.__db__.session.commit()
        return self._created_response(self.to_dict(resource))

    def delete(self, resource_id):
        """Return response to HTTP DELETE request."""
        resource = self._resource(resource_id)
        self.__db__.session.delete(resource)
        self.__db__.session.commit()
        return self._no_content_response()

    @verify_fields
    def put(self, resource_id):
        """Return response to HTTP PUT request."""
        resource = self._resource(resource_id)
        if resource is None:
            resource = self.__model__(   # pylint: disable=not-callable
                **request.json)
        else:
            resource.from_dict(request.json)
        self.__db__.session.add(resource)
        self.__db__.session.commit()
        return self._created_response(self.to_dict(resource))

    @verify_fields
    def patch(self, resource_id):
        """Return response to HTTP PATCH request."""
        resource = self._resource(resource_id)
        resource.from_dict(request.json)
        self.__db__.session.add(resource)
        self.__db__.session.commit()
        return self._created_response(self.to_dict(resource))

    def _resource(self, resource_id):
        """Return resource represented by this *resource_id*."""
        resource = self.__db__.session.query(self.__model__).get(resource_id)
        if not resource:
            return None
        return resource

    @staticmethod
    def _no_content_response():
        """Return an HTTP 204 "No Content" response."""
        response = make_response()
        response.status_code = 204
        return response

    @staticmethod
    def _created_response(resource):
        """Return an HTTP 201 "Created" response."""
        response = jsonify(resource)
        response.status_code = 201
        return response

    @staticmethod
    def to_dict(item):
        """Return dict representation of class by iterating over database
        columns."""
        value = {}
        for column in item.__table__.columns:
            attribute = getattr(item, column.name)
            if isinstance(attribute, datetime.datetime):
                attribute = str(attribute)
            value[column.name] = attribute
        return value


