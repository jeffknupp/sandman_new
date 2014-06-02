"""Admin module for sandman."""
from __future__ import absolute_import
from flask import Blueprint, render_template

admin = Blueprint('admin', __name__)


@admin.route('/')
def home():
    """Show the base admin view."""
    return render_template('admin/home.html')
