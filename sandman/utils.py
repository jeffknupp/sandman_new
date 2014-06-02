"""Utility functions for sandman."""
from functools import wraps

from flask import request

from sandman.exception import BadRequestException, ForbiddenException


def verify_fields(function):
    """A decorator to automatically verify all required JSON fields
    have been sent."""
    @wraps(function)
    def decorated(instance, *args, **kwargs):
        """The decorator function."""
        data = request.get_json(force=True, silent=True)
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
