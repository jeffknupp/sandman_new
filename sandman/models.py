"""SQLAlchemy-based models for use in sandman."""
import datetime
import decimal

from flask import jsonify, request, make_response, g, render_template
from flask.views import MethodView
from flask.ext.sqlalchemy import SQLAlchemy  # pylint:disable=no-name-in-module,import-error

from sandman.exception import (
    NotFoundException,
    BadRequestException,
    )
from sandman.utils import verify_fields
from sandman.response import collection_as_dict, resource_as_dict
from sandman.content_negotiation import (
    _get_acceptable_response_type,
    HTML,
    JSON
    )

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
    __app__ = None
    __endpoint__ = None

    def get(self, resource_id=None):
        """Return response to HTTP GET request."""
        if resource_id is None:
            return self._all_resources()
        else:
            resource = self._resource(resource_id)
            if not resource:
                raise NotFoundException
            return self._single_resource(self.to_dict(resource))

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

        content_type = _get_acceptable_response_type()
        if content_type == JSON:
            response = jsonify(collection_as_dict(resources, self))
            response.status_code = 200
            return response
        else:
            resources = collection_as_dict(resources, self)
            assert content_type == HTML
            return render_template(
                'collection.html',
                resources=resources)



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
            raise NotFoundException

    def _resource(self, resource_id):
        """Return resource represented by this *resource_id*."""
        resource = _get_session().query(self.__model__).get(resource_id)
        return jsonify(resource_as_dict(resource, resource_id, self))

    @staticmethod
    def _no_content_response():
        """Return an HTTP 204 "No Content" response."""
        response = make_response()
        response.status_code = 204
        return response

    @staticmethod
    def _created_response(resource):
        """Return an HTTP 201 "Created" response."""
        content_type = _get_acceptable_response_type()
        if content_type == JSON:
            response = jsonify(resource)
            response.status_code = 201
        else:
            assert content_type == HTML
            return render_template('resource.html', resource=resource)

    def to_dict(self, item):
        """Return dict representation of class by iterating over database
        columns."""
        value = {}
        for column in item.__table__.columns:
            attribute = getattr(item, column.name)
            if isinstance(attribute, datetime.datetime):
                attribute = str(attribute)
            if isinstance(attribute, decimal.Decimal):
                attribute = str(attribute)
            value[column.name] = attribute
            value['links'] = links(item, self.__endpoint__)
        return value

    def resource_uri(self):
        primary_key_value = (self.__model__, self.primarky_key())
        return '/{}/{}'.format(self.__endpoint__,
                primary_key_value.property.value)

    def primarky_key(self):
        """Return the name of the primary key column of the underlying
        model."""
        return self.__model__.__table__.primary_key.columns.values()[0].name

    def _single_resource(self, resource):
        content_type = _get_acceptable_response_type()
        if content_type == JSON:
            response = jsonify(resource)
            response.status_code = 200
        else:
            assert content_type == HTML
            return render_template(
                'resource.html',
                resource=resource,
                tablename=self.__model__.__name__,
                primary_key=self.primarky_key())

    @classmethod
    def endpoint(cls):
        if hasattr(cls, '__endpoint__') and cls.__endpoint__ is not None:
            return cls.__endpoint__
        else:
            cls.__endpoint__ = cls.__tablename__.lower() + 's'
            return cls.__endpoint__

def links(item, endpoint):
    """Return a list of links for endpoints related to the resource."""
    links = []
    for foreign_key in item.__table__.foreign_keys:
        column = foreign_key.column.name
        column_value = getattr(item, column, None)
        if column_value:
            table = foreign_key.column.table.name
            links.append({'rel': 'related', 'uri': '/{}/{}'.format(
                table.lower() + 's', column_value)})
    links.append({'rel': 'self', 'uri': '/{}/{}'.format(endpoint, item.resource_id)})
    return links
