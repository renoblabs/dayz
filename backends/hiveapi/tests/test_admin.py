"""Tests for admin endpoints."""

import pytest
from fastapi import status
from datetime import datetime, timedelta

from app.config import settings


# Known admin credentials used throughout these tests. The admin router is
# protected by HTTP Basic auth (require_admin), so every request must supply
# valid credentials.
ADMIN_USER = "admin"
ADMIN_PASS = "test-admin-password"
ADMIN_AUTH = (ADMIN_USER, ADMIN_PASS)


@pytest.fixture(autouse=True)
def admin_credentials():
    """Configure known admin credentials for the duration of each test.

    require_admin fails closed when ADMIN_PASSWORD is unset, so we set a known
    username/password here and restore the originals afterwards.
    """
    orig_user = settings.ADMIN_USERNAME
    orig_pass = settings.ADMIN_PASSWORD
    settings.ADMIN_USERNAME = ADMIN_USER
    settings.ADMIN_PASSWORD = ADMIN_PASS
    try:
        yield
    finally:
        settings.ADMIN_USERNAME = orig_user
        settings.ADMIN_PASSWORD = orig_pass


class TestAdminAuth:
    """Tests for admin Basic-auth protection on the whole router."""

    def test_overview_requires_auth(self, client):
        """No credentials -> 401 Unauthorized."""
        response = client.get("/v1/admin/overview")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_events_requires_auth(self, client):
        """No credentials on events endpoint -> 401 Unauthorized."""
        response = client.get("/v1/admin/events")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_overview_wrong_password(self, client):
        """Wrong password -> 401 Unauthorized."""
        response = client.get(
            "/v1/admin/overview", auth=(ADMIN_USER, "wrong-password")
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_overview_wrong_username(self, client):
        """Wrong username -> 401 Unauthorized."""
        response = client.get(
            "/v1/admin/overview", auth=("not-admin", ADMIN_PASS)
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_overview_correct_auth_returns_data(self, client, sample_character):
        """Correct credentials still return data."""
        response = client.get("/v1/admin/overview", auth=ADMIN_AUTH)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "players" in data
        assert "characters" in data


class TestAdminOverview:
    """Tests for admin overview endpoint."""

    def test_overview_returns_counts(self, client, sample_character):
        """Test that overview returns entity counts."""
        response = client.get("/v1/admin/overview", auth=ADMIN_AUTH)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "players" in data
        assert "characters" in data
        assert "servers" in data
        assert "recent_events" in data
        assert "timestamp" in data

        # Should have at least one of each from fixtures
        assert data["players"] >= 1
        assert data["characters"] >= 1
        assert data["servers"] >= 1

    def test_overview_timestamp_format(self, client):
        """Test that timestamp is in ISO format."""
        response = client.get("/v1/admin/overview", auth=ADMIN_AUTH)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should be able to parse as ISO datetime
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert isinstance(timestamp, datetime)


class TestAdminEvents:
    """Tests for admin events endpoint."""

    def test_get_events_default(self, client, sample_character):
        """Test getting events with default parameters."""
        # Create some events first
        from app.db.models import Event
        from app.deps import get_db

        response = client.get("/v1/admin/events", auth=ADMIN_AUTH)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_events_with_limit(self, client, test_db):
        """Test getting events with limit parameter."""
        # Create multiple events
        from app.db.models import Event
        import uuid

        for i in range(10):
            event = Event(
                id=str(uuid.uuid4()),
                type=f"test_event_{i}",
                payload_json={"index": i}
            )
            test_db.add(event)
        test_db.commit()

        response = client.get("/v1/admin/events?limit=5", auth=ADMIN_AUTH)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 5

    def test_get_events_with_type_filter(self, client, test_db):
        """Test filtering events by type."""
        from app.db.models import Event
        import uuid

        # Create events of different types
        event1 = Event(id=str(uuid.uuid4()), type="character_created", payload_json={})
        event2 = Event(id=str(uuid.uuid4()), type="inventory_updated", payload_json={})
        test_db.add_all([event1, event2])
        test_db.commit()

        response = client.get(
            "/v1/admin/events?event_type=character_created", auth=ADMIN_AUTH
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned events should be of the requested type
        for event in data:
            assert event["type"] == "character_created"

    def test_get_events_with_server_filter(self, client, test_db, sample_server):
        """Test filtering events by server_id."""
        from app.db.models import Event
        import uuid

        event = Event(
            id=str(uuid.uuid4()),
            type="test_event",
            server_id=sample_server.id,
            payload_json={}
        )
        test_db.add(event)
        test_db.commit()

        response = client.get(
            f"/v1/admin/events?server_id={sample_server.id}", auth=ADMIN_AUTH
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned events should be for the requested server
        for event in data:
            if event["server_id"]:
                assert event["server_id"] == sample_server.id

    def test_get_events_with_object_filter(self, client, test_db, sample_character):
        """Test filtering events by object_id."""
        from app.db.models import Event
        import uuid

        event = Event(
            id=str(uuid.uuid4()),
            type="character_updated",
            object_id=sample_character.id,
            payload_json={}
        )
        test_db.add(event)
        test_db.commit()

        response = client.get(
            f"/v1/admin/events?object_id={sample_character.id}", auth=ADMIN_AUTH
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned events should be for the requested object
        for event in data:
            if event["object_id"]:
                assert event["object_id"] == sample_character.id

    def test_get_events_limit_validation(self, client):
        """Test that limit parameter is validated."""
        # Limit too high
        response = client.get("/v1/admin/events?limit=2000", auth=ADMIN_AUTH)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Limit too low
        response = client.get("/v1/admin/events?limit=0", auth=ADMIN_AUTH)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
