"""Tests for character endpoints."""

import uuid

import pytest
from fastapi import status


class TestClaimCharacter:
    """Tests for character claim endpoint."""

    def test_claim_creates_new_player_and_character(self, client, sample_cluster, sample_server, auth_header):
        """Test that claiming creates a new player and character if they don't exist."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-new-player-123",
                "cluster_id": sample_cluster.id,
                "position": {"x": 100.0, "y": 50.0, "z": 200.0},
                "stats": {"health": 100, "blood": 5000}
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "player_id" in data
        assert data["cluster_id"] == sample_cluster.id
        assert data["owned_by_server"] == sample_server.id
        assert data["life_state"] == "alive"
        assert data["position"] == {"x": 100.0, "y": 50.0, "z": 200.0}

    def test_claim_existing_character(self, client, sample_character, sample_cluster, sample_server, auth_header):
        """Test claiming an existing character."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": sample_character.player.platform_uid,
                "cluster_id": sample_cluster.id,
                "position": {"x": 150.0, "y": 60.0, "z": 250.0}
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_character.id
        assert data["position"] == {"x": 150.0, "y": 60.0, "z": 250.0}

    def test_claim_with_invalid_cluster(self, client, sample_server, auth_header):
        """Test claiming with non-existent cluster."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-test-123",
                "cluster_id": "non-existent-cluster",
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Cluster not found" in response.json()["detail"]

    def test_claim_server_not_in_cluster(self, client, test_db, sample_cluster, auth_header_for):
        """A server authenticated against a different cluster cannot claim here (403)."""
        from app.db.models import Cluster, Server

        # A second cluster + server that the token will authenticate as.
        other_cluster = Cluster(
            id=str(uuid.uuid4()),
            tenant_id=sample_cluster.tenant_id,
            name="Other Cluster",
            policy_json={},
        )
        test_db.add(other_cluster)
        test_db.flush()
        other_server = Server(
            id=str(uuid.uuid4()),
            cluster_id=other_cluster.id,
            name="Other Server",
            host_fingerprint=f"test-fingerprint-{uuid.uuid4()}",
            public_key_pem="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
            status="active",
        )
        test_db.add(other_server)
        test_db.commit()

        # Token authenticates as other_server, but the claim targets sample_cluster.
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-test-123",
                "cluster_id": sample_cluster.id,
            },
            headers=auth_header_for(other_server),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_claim_no_token(self, client, sample_cluster):
        """Claiming without an Authorization header is rejected (401)."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-test-123",
                "cluster_id": sample_cluster.id,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCharacterHeartbeat:
    """Tests for character heartbeat endpoint."""

    def test_heartbeat_updates_character(self, client, sample_character, auth_header):
        """Test that heartbeat updates character data."""
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": sample_character.id,
                "position": {"x": 300.0, "y": 100.0, "z": 400.0},
                "stats": {"health": 85, "blood": 4500}
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_character.id
        assert data["position"] == {"x": 300.0, "y": 100.0, "z": 400.0}
        assert data["stats"]["health"] == 85
        assert data["stats"]["blood"] == 4500

    def test_heartbeat_with_invalid_character(self, client, auth_header):
        """Test heartbeat with non-existent character."""
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": "non-existent-character",
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Character not found" in response.json()["detail"]

    def test_heartbeat_merges_stats(self, client, sample_character, auth_header):
        """Test that heartbeat merges stats instead of replacing."""
        # Initial stats
        initial_stats = sample_character.stats_json.copy()

        # Send heartbeat with partial stats
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": sample_character.id,
                "stats": {"health": 75}
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check that only health was updated, blood remains
        assert data["stats"]["health"] == 75
        assert data["stats"]["blood"] == initial_stats.get("blood", 5000)

    def test_heartbeat_idor_other_server_forbidden(self, client, test_db, sample_character, sample_cluster, auth_header_for):
        """A token for a different server cannot heartbeat someone else's character (403)."""
        from app.db.models import Server

        # A second server (same cluster) that does NOT own sample_character.
        other_server = Server(
            id=str(uuid.uuid4()),
            cluster_id=sample_cluster.id,
            name="Attacker Server",
            host_fingerprint=f"test-fingerprint-{uuid.uuid4()}",
            public_key_pem="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
            status="active",
        )
        test_db.add(other_server)
        test_db.commit()

        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": sample_character.id,
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            },
            headers=auth_header_for(other_server),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_heartbeat_no_token(self, client, sample_character):
        """Heartbeat without an Authorization header is rejected (401)."""
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": sample_character.id,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
