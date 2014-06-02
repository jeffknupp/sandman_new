from flask import jsonify

from sandman import app
from sandman.exception import InvalidAPIUsage
from sandman.utils import _get_session

JSON, HTML = range(2)
JSON_CONTENT_TYPES = set(['application/json', ])
HTML_CONTENT_TYPES = set(['text/html', 'application/x-www-form-urlencoded'])
ALL_CONTENT_TYPES = set(['*/*'])
ACCEPTABLE_CONTENT_TYPES = (
    JSON_CONTENT_TYPES |
    HTML_CONTENT_TYPES |
    ALL_CONTENT_TYPES)

FORWARDED_EXCEPTION_MESSAGE = 'Request could not be completed. Exception: [{}]'
FORBIDDEN_EXCEPTION_MESSAGE = """Method [{}] not acceptable for resource \
type [{}].  Acceptable methods: [{}]"""
UNSUPPORTED_CONTENT_TYPE_MESSAGE = 'Content-type [{types}] not supported.'


def _get_acceptable_response_type(request):
    """Return the Mimetype of this request."""
    if ('Accept' not in request.headers or request.headers['Accept'] in
            ALL_CONTENT_TYPES):
        return JSON

    acceptable_content_types = set(
        request.headers['ACCEPT'].strip().split(','))

    if acceptable_content_types & HTML_CONTENT_TYPES:
        return HTML

    elif acceptable_content_types & JSON_CONTENT_TYPES:
        return JSON

    else:
        # HTTP 406 Not Acceptable
        raise InvalidAPIUsage(406)


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
