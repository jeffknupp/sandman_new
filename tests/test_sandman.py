"""Tests for sandman."""
import json
import os
import shutil

import pytest

from sandman import app as sandman_app, reflect_all, init_app
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
    sandman_app.testing = True
    db.init_app(sandman_app)
    try:
        reflect_all()
    except AssertionError:
        pass

    yield sandman_app

    os.unlink(DB_LOCATION)


@pytest.yield_fixture(scope='function')
def init():
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
    sandman_app.testing = True
    db.init_app(sandman_app)
    import models

    try:
        init_app(sandman_app, [models.Artist])
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


def test_get_collection_existing_model(init):
    """Can we get a collection as JSON?"""
    with init.test_client() as test:
        response = test.get('/artist')
        json_response = json.loads(response.get_data())
        assert len(json_response['resources']) == 275


def test_get_resource(app):
    """Can we get a resource as JSON?"""
    with app.test_client() as test:
        response = test.get('/artist/1')
        json_response = json.loads(response.get_data())
        assert json_response['Name'] == 'AC/DC'


def test_get_resource_with_datetime(app):
    """Can we get a resource with a datetime field as JSON?"""
    with app.test_client() as test:
        response = test.get('/datetime/1')
        json_response = json.loads(response.get_data())
        assert 'time' in json_response



def test_get_non_existant_resource(app):
    """Can we get a resource as JSON?"""
    with app.test_client() as test:
        response = test.get('/artist/300')
        assert response.status_code == 404


def test_get_paginated_collection(app):
    """Can we get a single page of a collection as JSON?"""
    with app.test_client() as test:
        response = test.get('/artist?page=2')
        json_response = json.loads(response.get_data())
        assert len(json_response['resources']) == 20
        assert json_response['resources'][0]['ArtistId'] == 41
        assert json_response['resources'][19]['ArtistId'] == 60


def test_post_resource(app):
    """Can we POST a resource?"""
    with app.test_client() as test:
        response = test.post(
            '/artist',
            data=json.dumps({'Name': 'Jeff Knupp'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 201

def test_post_no_data(app):
    """Do we get a 400 error if we POST without data?"""
    with app.test_client() as test:
        response = test.post(
            '/artist',
            data=json.dumps({}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 400


def test_post_wrong_data(app):
    """Do we get a 400 error if we POST without including required data."""
    with app.test_client() as test:
        response = test.post(
            '/artist',
            data=json.dumps({'foo': 'bar'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 403


def test_existing_resource(app):
    """Do we get a 400 error if we POST a resource that already exists?"""
    with app.test_client() as test:
        response = test.post(
            '/artist',
            data=json.dumps({'ArtistId': 1, 'Name': 'AC/DC'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 400


def test_delete_resource(app):
    """Can we successfully DELETE a resource?"""
    with app.test_client() as test:
        response = test.delete('/album/1')
        assert response.status_code == 204


def test_put_existing_resource(app):
    """Can we successfully PUT an existing resource?"""
    with app.test_client() as test:
        response = test.put(
            '/artist/1',
            data=json.dumps({'ArtistId': 1, 'Name': 'Jeff/DC'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 204
        response = test.get('/artist/1')
        assert json.loads(response.get_data())['Name'] == 'Jeff/DC'


def test_put_new_resource(app):
    """Can we successfully PUT an existing resource?"""
    with app.test_client() as test:
        response = test.put(
            '/artist/276',
            data=json.dumps({'ArtistId': 276, 'Name': 'Jeff/DC'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 201
        response = test.get('/artist/276')
        assert json.loads(response.get_data())['Name'] == 'Jeff/DC'


def test_patch(app):
    """Can we successfully patch an existing resource?"""
    with app.test_client() as test:
        response = test.patch(
            '/artist/1',
            data=json.dumps({'Name': 'Jeff/DC'}),
            headers={'Content-type': 'application/json'})
        assert response.status_code == 201
        response = test.get('/artist/276')
        assert json.loads(response.get_data())['ArtistId'] == 1
