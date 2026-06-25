"""Tests for inventory endpoints."""

import pytest
from fastapi import status


class TestSetInventory:
    """Tests for inventory set endpoint."""

    def test_set_inventory_successfully(self, client, sample_character, auth_header):
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
                "slots": new_inventory
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["character_id"] == sample_character.id
        assert "checksum" in data
        assert data["conflict"] is False

    def test_set_inventory_with_invalid_character(self, client, sample_server, auth_header):
        """Test setting inventory with non-existent character."""
        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": "non-existent-character",
                "slots": {}
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Character not found" in response.json()["detail"]

    def test_set_inventory_with_client_checksum_match(self, client, sample_character, auth_header):
        """Test setting inventory with matching client checksum."""
        from app.services.inventory import compute_inventory_checksum

        new_inventory = {"slots": {"0": {"item": "Bandage"}}}
        checksum = compute_inventory_checksum(new_inventory)

        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "slots": new_inventory,
                "client_checksum": checksum
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is False

    def test_set_inventory_with_client_checksum_mismatch(self, client, sample_character, auth_header):
        """Test setting inventory with mismatched client checksum."""
        new_inventory = {"slots": {"0": {"item": "Bandage"}}}

        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "slots": new_inventory,
                "client_checksum": "wrong-checksum"
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is True
        assert "conflict_details" in data

    def test_set_inventory_requires_auth(self, client, sample_character):
        """A request with no Bearer token is rejected with 401."""
        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "slots": {"slots": {}}
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_set_inventory_idor_blocked(self, client, sample_character, auth_header_for,
                                        test_db, sample_cluster):
        """A token for a different server cannot set another server's character (403)."""
        from app.db.models import Server
        import uuid

        other_server = Server(
            id=str(uuid.uuid4()),
            cluster_id=sample_cluster.id,
            name="Other Server",
            host_fingerprint=f"other-fingerprint-{uuid.uuid4()}",
            public_key_pem="-----BEGIN PUBLIC KEY-----\nother\n-----END PUBLIC KEY-----",
            status="active",
        )
        test_db.add(other_server)
        test_db.commit()
        test_db.refresh(other_server)

        response = client.post(
            "/v1/inventory/set",
            json={
                "character_id": sample_character.id,
                "slots": {"slots": {"0": {"item": "StolenLoot"}}}
            },
            headers=auth_header_for(other_server),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestApplyInventoryOps:
    """Tests for inventory apply operations endpoint."""

    def test_apply_ops_successfully(self, client, sample_character, test_db, auth_header):
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
                "ops": ops,
                "base_checksum": sample_character.inventory_checksum
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is False
        assert "checksum" in data

    def test_apply_ops_with_conflict(self, client, sample_character, test_db, auth_header):
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
                "ops": ops,
                "base_checksum": "wrong-checksum"
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict"] is True
        assert "conflict_details" in data

    def test_apply_ops_with_invalid_character(self, client, sample_server, auth_header):
        """Test applying operations with non-existent character."""
        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": "non-existent-character",
                "ops": [],
                "base_checksum": "test-checksum"
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Character not found" in response.json()["detail"]

    def test_apply_ops_requires_auth(self, client, sample_character):
        """A request with no Bearer token is rejected with 401."""
        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": sample_character.id,
                "ops": [],
                "base_checksum": "test-checksum"
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_apply_ops_idor_blocked(self, client, sample_character, auth_header_for,
                                    test_db, sample_cluster):
        """A token for a different server cannot apply ops to another server's character (403)."""
        from app.db.models import Server
        import uuid

        other_server = Server(
            id=str(uuid.uuid4()),
            cluster_id=sample_cluster.id,
            name="Other Server",
            host_fingerprint=f"other-fingerprint-{uuid.uuid4()}",
            public_key_pem="-----BEGIN PUBLIC KEY-----\nother\n-----END PUBLIC KEY-----",
            status="active",
        )
        test_db.add(other_server)
        test_db.commit()
        test_db.refresh(other_server)

        ops = [{"op": "set", "path": ["slots", "1"], "value": {"item": "StolenLoot"}}]

        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": sample_character.id,
                "ops": ops,
                "base_checksum": "test-checksum"
            },
            headers=auth_header_for(other_server),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_apply_ops_rejects_too_many_ops(self, client, sample_character, auth_header):
        """Oversized op batches are rejected with 400 to prevent unbounded work."""
        ops = [{"op": "set", "path": ["slots", str(i)], "value": {"item": "x"}} for i in range(201)]

        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": sample_character.id,
                "ops": ops,
                "base_checksum": "test-checksum"
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_apply_ops_rejects_deep_path(self, client, sample_character, auth_header):
        """Excessively deep op paths are rejected with 400."""
        deep_path = [f"level{i}" for i in range(9)]
        ops = [{"op": "set", "path": deep_path, "value": {"item": "x"}}]

        response = client.post(
            "/v1/inventory/apply",
            json={
                "character_id": sample_character.id,
                "ops": ops,
                "base_checksum": "test-checksum"
            },
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
