"""Tests for authentication endpoints."""

import pytest
from fastapi import status


@pytest.fixture
def dev_login(monkeypatch):
    """Enable the dev-only login shortcut for a single test.

    The /server-login dev shortcut only runs when REQUEST_SIGNATURE_REQUIRED is
    False AND ENV is in ('dev', 'test'). conftest sets ENV='test' and leaves
    REQUEST_SIGNATURE_REQUIRED=True (the secure default), so tests that want the
    shortcut must explicitly opt in. monkeypatch restores the original value at
    test teardown.
    """
    monkeypatch.setattr(
        "app.routers.auth.settings.REQUEST_SIGNATURE_REQUIRED", False
    )


class TestServerLogin:
    """Tests for server login endpoint."""

    def test_login_with_valid_server(self, client, sample_server, dev_login):
        """Test successful server login returns a non-empty bearer token."""
        response = client.post(
            "/v1/auth/server-login",
            json={"server_id": sample_server.id}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        # Token must be a non-empty bearer string.
        assert isinstance(data["access_token"], str)
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

    def test_login_with_invalid_server(self, client, dev_login):
        """Test login with non-existent server."""
        response = client.post(
            "/v1/auth/server-login",
            json={"server_id": "non-existent-server-id"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid server credentials" in response.json()["detail"]

    def test_login_with_missing_server_id(self, client, dev_login):
        """Test login with missing server_id."""
        response = client.post(
            "/v1/auth/server-login",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_updates_last_seen(self, client, sample_server, test_db, dev_login):
        """Test that login updates server's last_seen_at."""
        from app.db.models import Server

        # Get initial last_seen_at
        initial_last_seen = sample_server.last_seen_at

        # Login
        response = client.post(
            "/v1/auth/server-login",
            json={"server_id": sample_server.id}
        )

        assert response.status_code == status.HTTP_200_OK

        # Refresh server from DB
        test_db.refresh(sample_server)

        # Check that last_seen_at was updated
        assert sample_server.last_seen_at is not None
        if initial_last_seen:
            assert sample_server.last_seen_at >= initial_last_seen

    def test_login_required_signature_no_proof_rejected(
        self, client, sample_server, monkeypatch
    ):
        """With signatures required and no proof supplied, login must be rejected (401).

        This guards against the dev shortcut being reachable when
        REQUEST_SIGNATURE_REQUIRED is True (the production-like default).
        """
        monkeypatch.setattr(
            "app.routers.auth.settings.REQUEST_SIGNATURE_REQUIRED", True
        )

        response = client.post(
            "/v1/auth/server-login",
            json={"server_id": sample_server.id}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "proof" in response.json()["detail"].lower()

    def test_login_with_valid_signature(self, client, sample_server, test_db):
        """Test login with valid RSA signature."""
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        import base64
        from unittest.mock import patch

        # Generate key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()

        # Get PEM
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Update server with public key
        sample_server.public_key_pem = pem.decode('utf-8')
        test_db.commit()

        # Sign server_id
        signature = private_key.sign(
            sample_server.id.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        proof = base64.b64encode(signature).decode('utf-8')

        # Force signature requirement
        with patch("app.routers.auth.settings.REQUEST_SIGNATURE_REQUIRED", True):
            response = client.post(
                "/v1/auth/server-login",
                json={
                    "server_id": sample_server.id,
                    "proof": proof
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data

    def test_login_with_invalid_signature(self, client, sample_server, test_db):
        """Test login with invalid RSA signature."""
        from unittest.mock import patch

        # Force signature requirement
        with patch("app.routers.auth.settings.REQUEST_SIGNATURE_REQUIRED", True):
            response = client.post(
                "/v1/auth/server-login",
                json={
                    "server_id": sample_server.id,
                    "proof": "invalid-base64-proof"
                }
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
