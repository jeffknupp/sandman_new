"""Tests for sandman."""
import json
import os
import shutil

import pytest

from sandman import app as sandman_app, reflect_all
from sandman.models import db

DB_LOCATION = os.path.join(os.getcwd(), 'tests', 'chinook.sqlite3')


@pytest.yield_fixture(scope='function')
def app():
    """Fixture to provide the application object and initialize the
    database."""
    sandman_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + DB_LOCATION
    shutil.copy(
        os.path.join(
            os.getcwd(),
            'tests',
            'data',
            'chinook.sqlite3'),
        DB_LOCATION)

    db.init_app(sandman_app)
    try:
        reflect_all()
    except AssertionError:
        pass

    yield sandman_app

    os.unlink(DB_LOCATION)


def test_get_collection(app):
    """Can we get a collection as JSON?"""
    with app.test_client() as test:
        response = test.get('/artist')
        json_response = json.loads(response.get_data())
        assert len(json_response['resources']) == 275

def test_post_resource(app):
    with app.test_client() as test:
        response = test.post(
            '/artist',
            data=json.dumps({'Name': 'Jeff Knupp'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 201
