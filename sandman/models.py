"""SQLAlchemy-based models for use in sandman."""
import datetime

from flask import jsonify, request, make_response, g
from flask.views import MethodView
from flask.ext.sqlalchemy import SQLAlchemy  # pylint:disable=no-name-in-module,import-error,

from sandman.exception import (
    NotFoundException,
    BadRequestException,
    )
from sandman.utils import verify_fields

db = SQLAlchemy()  # pylint: disable=invalid-name


def _get_session():
    """Return (and memoize) a database session"""
    session = getattr(g, '_session', None)
    if session is None:
        session = g._session = db.session()
    return session


class Model(MethodView):
    """Base class for all resources."""

    __model__ = None

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
        query_arguments = request.args
        filters = []
        order = []
        resources = None
        if query_arguments:
            for key, value in query_arguments.items():
                if key == 'page':
                    continue
                if value.startswith('%'):
                    filters.append(getattr(self.__model__, key).like(
                        str(value), escape='/'))
                elif key == 'sort':
                    order.append(getattr(self.__model__, value))
                elif key:
                    filters.append(getattr(self.__model__, key) == value)
        if filters:
            print filters
            resources = _get_session().query(  # pylint: disable=star-args
                self.__model__).filter(*filters)
        else:
            resources = _get_session().query(self.__model__)
        if order:
            resources = resources.order_by(  # pylint: disable=star-args
                *order)
        if 'page' in query_arguments:
            resources = resources.limit(20).offset(
                20 * int(request.args['page']))
        resources = resources.all()

        return jsonify(
            {'resources': [self.to_dict(resource) for resource in resources]})

    @verify_fields
    def post(self):
        """Return response to HTTP POST request."""
        # pylint: disable=unused-argument
        resource = _get_session().query(
            self.__model__).filter_by(**request.json).first()
        # resource already exists; don't create it again
        if resource:
            raise BadRequestException('resource already exists')
        resource = self.__model__(  # pylint: disable=not-callable
            **request.json)
        _get_session().add(resource)
        _get_session().commit()
        return self._created_response(self.to_dict(resource))

    def delete(self, resource_id):
        """Return response to HTTP DELETE request."""
        resource = self._resource(resource_id)
        _get_session().delete(resource)
        _get_session().commit()
        return self._no_content_response()

    @verify_fields
    def put(self, resource_id):
        """Return response to HTTP PUT request."""
        resource = self._resource(resource_id)
        if resource is None:
            resource = self.__model__(   # pylint: disable=not-callable
                **request.json)
            _get_session().add(resource)
            _get_session().commit()
            return self._created_response(self.to_dict(resource))
        else:
            resource = self.__model__(  # pylint: disable=not-callable
                **request.json)
            _get_session().merge(resource)
            _get_session().commit()
            return self._no_content_response()

    @verify_fields
    def patch(self, resource_id):
        """Return response to HTTP PATCH request."""
        resource = self._resource(resource_id)
        if resource:
            for key, value in request.json.items():
                setattr(resource, key, value)
            _get_session().merge(resource)
            _get_session().commit()
            resource = self._resource(resource_id)
            return self._no_content_response()
        else:
            resource = self.__model__(  # pylint: disable=not-callable
                **request.json)
            _get_session().add(resource)
            _get_session().commit()
            return self._created_response(self.to_dict(resource))

    def _resource(self, resource_id):
        """Return resource represented by this *resource_id*."""
        resource = _get_session().query(self.__model__).get(resource_id)
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
