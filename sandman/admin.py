"""Admin module for sandman."""
from __future__ import absolute_import
from flask import Blueprint, render_template, send_file

admin = Blueprint('admin', __name__)


@admin.route('/')
def home():
    """Show the base admin view."""
    return render_template('admin/home.html')

@admin.route('/<resource>')
def resource_page(resource):
    """Show the base admin view."""
    return send_file('templates/admin/' + resource)
