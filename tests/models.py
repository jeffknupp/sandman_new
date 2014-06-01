"""Models for sandman tests."""
from sandman.models import Model


class Artist(Model):
    """The artist model."""
    __tablename__ = 'Artist'
