"""Minimal Flask app for running Alembic migrations without importing full app stack."""
from flask import Flask
from slms.extensions import db, migrate
import os

class _Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///slms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def create_app():
    app = Flask(__name__)
    app.config.from_object(_Config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure models are loaded for Alembic metadata
    import slms.models  # noqa: F401

    return app
