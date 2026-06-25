"""Tests for character endpoints."""

import pytest
from fastapi import status


class TestClaimCharacter:
    """Tests for character claim endpoint."""

    def test_claim_creates_new_player_and_character(self, client, sample_cluster, sample_server):
        """Test that claiming creates a new player and character if they don't exist."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-new-player-123",
                "cluster_id": sample_cluster.id,
                "server_id": sample_server.id,
                "position": {"x": 100.0, "y": 50.0, "z": 200.0},
                "stats": {"health": 100, "blood": 5000}
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "player_id" in data
        assert data["cluster_id"] == sample_cluster.id
        assert data["owned_by_server"] == sample_server.id
        assert data["life_state"] == "alive"
        assert data["position"] == {"x": 100.0, "y": 50.0, "z": 200.0}

    def test_claim_existing_character(self, client, sample_character, sample_cluster, sample_server):
        """Test claiming an existing character."""
        # Get the player platform_uid


        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": sample_character.player.platform_uid,
                "cluster_id": sample_cluster.id,
                "server_id": sample_server.id,
                "position": {"x": 150.0, "y": 60.0, "z": 250.0}
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_character.id
        assert data["position"] == {"x": 150.0, "y": 60.0, "z": 250.0}

    def test_claim_with_invalid_cluster(self, client, sample_server):
        """Test claiming with non-existent cluster."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-test-123",
                "cluster_id": "non-existent-cluster",
                "server_id": sample_server.id
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Cluster not found" in response.json()["detail"]

    def test_claim_with_invalid_server(self, client, sample_cluster):
        """Test claiming with non-existent server."""
        response = client.post(
            "/v1/characters/claim",
            json={
                "platform_uid": "steam-test-123",
                "cluster_id": sample_cluster.id,
                "server_id": "non-existent-server"
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Server not found" in response.json()["detail"]


class TestCharacterHeartbeat:
    """Tests for character heartbeat endpoint."""

    def test_heartbeat_updates_character(self, client, sample_character):
        """Test that heartbeat updates character data."""
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "position": {"x": 300.0, "y": 100.0, "z": 400.0},
                "stats": {"health": 85, "blood": 4500}
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_character.id
        assert data["position"] == {"x": 300.0, "y": 100.0, "z": 400.0}
        assert data["stats"]["health"] == 85
        assert data["stats"]["blood"] == 4500

    def test_heartbeat_with_invalid_character(self, client, sample_server):
        """Test heartbeat with non-existent character."""
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": "non-existent-character",
                "server_id": sample_server.id
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Character not found" in response.json()["detail"]

    def test_heartbeat_merges_stats(self, client, sample_character):
        """Test that heartbeat merges stats instead of replacing."""
        # Initial stats
        initial_stats = sample_character.stats_json.copy()

        # Send heartbeat with partial stats
        response = client.post(
            "/v1/characters/heartbeat",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "stats": {"health": 75}
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check that only health was updated, blood remains
        assert data["stats"]["health"] == 75
        assert data["stats"]["blood"] == initial_stats.get("blood", 5000)
