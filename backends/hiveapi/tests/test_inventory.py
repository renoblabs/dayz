"""Tests for inventory endpoints."""

import pytest
from fastapi import status


class TestSetInventory:
    """Tests for inventory set endpoint."""

    def test_set_inventory_successfully(self, client, sample_character):
        """Test setting inventory successfully."""
        new_inventory = {
            "slots": {
                "0": {"item": "HockeyStick", "quantity": 1},
                "1": {"item": "BeerCan", "quantity": 3}
            }
        }

        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "slots": new_inventory
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["character_id"] == sample_character.id
        assert "checksum" in data
        assert data["conflict"] is False

    def test_set_inventory_with_invalid_character(self, client, sample_server):
        """Test setting inventory with non-existent character."""
        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": "non-existent-character",
                "server_id": sample_server.id,
                "slots": {}
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Character not found" in response.json()["detail"]

    def test_set_inventory_with_client_checksum_match(self, client, sample_character):
        """Test setting inventory with matching client checksum."""
        from app.services.inventory import compute_inventory_checksum

        new_inventory = {"slots": {"0": {"item": "Bandage"}}}
        checksum = compute_inventory_checksum(new_inventory)

        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "slots": new_inventory,
                "client_checksum": checksum
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is False

    def test_set_inventory_with_client_checksum_mismatch(self, client, sample_character):
        """Test setting inventory with mismatched client checksum."""
        new_inventory = {"slots": {"0": {"item": "Bandage"}}}

        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "slots": new_inventory,
                "client_checksum": "wrong-checksum"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is True
        assert "conflict_details" in data


class TestApplyInventoryOps:
    """Tests for inventory apply operations endpoint."""

    def test_apply_ops_successfully(self, client, sample_character, test_db):
        """Test applying inventory operations successfully."""
        from app.services.inventory import compute_inventory_checksum

        # Set initial inventory
        initial_inventory = {"slots": {"0": {"item": "Bandage", "quantity": 1}}}
        sample_character.inventory_json = initial_inventory
        sample_character.inventory_checksum = compute_inventory_checksum(initial_inventory)
        test_db.commit()
        test_db.refresh(sample_character)

        # Apply operations
        ops = [
            {"op": "set", "path": ["slots", "1"], "value": {"item": "HockeyStick", "quantity": 1}}
        ]

        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "ops": ops,
                "base_checksum": sample_character.inventory_checksum
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is False
        assert "checksum" in data

    def test_apply_ops_with_conflict(self, client, sample_character, test_db):
        """Test applying operations with checksum conflict."""
        from app.services.inventory import compute_inventory_checksum

        # Set initial inventory
        initial_inventory = {"slots": {"0": {"item": "Bandage"}}}
        sample_character.inventory_json = initial_inventory
        sample_character.inventory_checksum = compute_inventory_checksum(initial_inventory)
        test_db.commit()
        test_db.refresh(sample_character)

        # Try to apply with wrong base checksum
        ops = [{"op": "set", "path": ["slots", "1"], "value": {"item": "HockeyStick"}}]

        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": sample_character.id,
                "server_id": sample_character.owned_by_server,
                "ops": ops,
                "base_checksum": "wrong-checksum"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is True
        assert "conflict_details" in data

    def test_apply_ops_with_invalid_character(self, client, sample_server):
        """Test applying operations with non-existent character."""
        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": "non-existent-character",
                "server_id": sample_server.id,
                "ops": [],
                "base_checksum": "test-checksum"
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Character not found" in response.json()["detail"]
