"""HTTP Response object utility functions and classes."""

from flask import jsonify

def collection_as_dict(resources, cls):
    """Return a collection JSONified."""
    for resource in resources:
        resource.resource_id = getattr(resource, cls.primarky_key())
    return {'resources': [cls.to_dict(resource) for resource in resources]}


def resource_as_dict(resource, resource_id, cls):
    if not resource:
        return None
    resource.resource_id = resource_id
    return resource
