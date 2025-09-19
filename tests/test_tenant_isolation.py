import os
from pathlib import Path

os.environ['DATABASE_URL'] = 'sqlite:///tenant_test.db'

import pytest
from flask import g
from werkzeug.exceptions import NotFound

from slms import create_app
from slms.extensions import db
from slms.models import League, Organization, SportType
from slms.blueprints.common.tenant import (
    get_object_or_404,
    org_query,
    tenant_required,
)


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SERVER_NAME="example.com",
        SQLALCHEMY_DATABASE_URI=os.environ['DATABASE_URL'],
    )

    def _league_detail(league_id):
        league = get_object_or_404(League, league_id)
        return {"id": league.id, "org_id": league.org_id}

    if 'league_detail' not in app.view_functions:
        app.add_url_rule("/leagues/<league_id>", 'league_detail', tenant_required(_league_detail))

    with app.app_context():
        db.session.remove()
        db.engine.dispose()
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
    Path('tenant_test.db').unlink(missing_ok=True)


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_org(name: str, slug: str) -> Organization:
    org = Organization(name=name, slug=slug)
    db.session.add(org)
    db.session.commit()
    return org


def test_resolve_tenant_via_header(app):
    with app.app_context():
        org = _create_org("Org One", "org-one")
        org_id = org.id

    with app.test_request_context("/", headers={"X-Org-Slug": "org-one"}):
        app.preprocess_request()
        assert g.org is not None
        assert g.org.id == org_id


def test_resolve_tenant_via_subdomain(app):
    with app.app_context():
        org = _create_org("Wildcats", "wildcats")
        org_slug = org.slug

    with app.test_request_context("/", base_url="https://wildcats.example.com"):
        app.preprocess_request()
        assert g.org is not None
        assert g.org.slug == org_slug


def test_org_query_scopes_results(app):
    with app.app_context():
        org1 = _create_org("Org One", "org1")
        org2 = _create_org("Org Two", "org2")
        org1_id = org1.id
        org1_slug = org1.slug
        org2_slug = org2.slug

    with app.test_request_context("/", headers={"X-Org-Slug": org1_slug}):
        app.preprocess_request()
        league = League(name="League 1", sport=SportType.BASKETBALL)
        db.session.add(league)
        db.session.commit()
        league_id = league.id
        assert league.org_id == org1_id

    with app.test_request_context("/", headers={"X-Org-Slug": org2_slug}):
        app.preprocess_request()
        assert org_query(League).filter_by(id=league_id).first() is None
        with pytest.raises(NotFound):
            get_object_or_404(League, league_id)

        league = db.session.get(League, league_id)
        if league is not None:
            league.name = "Hacked"
            with pytest.raises(PermissionError):
                db.session.commit()
            db.session.rollback()


def test_cross_org_route_returns_404(app, client):
    with app.app_context():
        org1 = _create_org("Org One", "org1")
        org2 = _create_org("Org Two", "org2")
        org1_id = org1.id
        org1_slug = org1.slug
        org2_slug = org2.slug

    with app.test_request_context("/", headers={"X-Org-Slug": org1_slug}):
        app.preprocess_request()
        league = League(name="League 1", sport=SportType.BASKETBALL)
        db.session.add(league)
        db.session.commit()
        league_id = league.id

    resp = client.get(f"/leagues/{league_id}", headers={"X-Org-Slug": org1_slug})
    assert resp.status_code == 200

    resp = client.get(f"/leagues/{league_id}", headers={"X-Org-Slug": org2_slug})
    assert resp.status_code == 404

    resp = client.get(f"/leagues/{league_id}")
    assert resp.status_code == 404
