"""
Pytest configuration and fixtures for DayZ HiveAPI tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os

from app.main import app
from app.db.models import Base
from app.deps import get_db

from app.config import settings

# Provide a signing secret so token-issuing endpoints work under test.
settings.JWT_SIGNING_SECRET = settings.JWT_SIGNING_SECRET or "test-signing-secret"

# Use configured database URL (PostgreSQL)
TEST_DATABASE_URL = settings.DB_URL

@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for the test session."""
    engine = create_engine(TEST_DATABASE_URL)
    # Create tables once for the session
    Base.metadata.create_all(bind=engine)
    yield engine
    # Drop tables after session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def test_db(db_engine):
    """Create a test database session with transaction rollback."""
    connection = db_engine.connect()
    transaction = connection.begin()
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def sample_tenant(test_db):
    """Create a sample tenant for testing."""
    from app.db.models import Tenant
    import uuid

    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Tenant",
        owner_id="test-owner-123",
        settings_json={}
    )
    test_db.add(tenant)
    test_db.commit()
    test_db.refresh(tenant)
    return tenant

@pytest.fixture
def sample_cluster(test_db, sample_tenant):
    """Create a sample cluster for testing."""
    from app.db.models import Cluster
    import uuid

    cluster = Cluster(
        id=str(uuid.uuid4()),
        tenant_id=sample_tenant.id,
        name="Test Cluster",
        policy_json={}
    )
    test_db.add(cluster)
    test_db.commit()
    test_db.refresh(cluster)
    return cluster

@pytest.fixture
def sample_server(test_db, sample_cluster):
    """Create a sample server for testing."""
    from app.db.models import Server
    import uuid

    server = Server(
        id=str(uuid.uuid4()),
        cluster_id=sample_cluster.id,
        name="Test Server",
        host_fingerprint=f"test-fingerprint-{uuid.uuid4()}",
        public_key_pem="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
        status="active"
    )
    test_db.add(server)
    test_db.commit()
    test_db.refresh(server)
    return server

@pytest.fixture
def sample_player(test_db):
    """Create a sample player for testing."""
    from app.db.models import Player
    import uuid

    player = Player(
        id=str(uuid.uuid4()),
        platform_uid=f"steam-{uuid.uuid4()}",
        reputation=0,
        meta={}
    )
    test_db.add(player)
    test_db.commit()
    test_db.refresh(player)
    return player

@pytest.fixture
def sample_character(test_db, sample_player, sample_cluster, sample_server):
    """Create a sample character for testing."""
    from app.db.models import Character
    import uuid

    character = Character(
        id=str(uuid.uuid4()),
        player_id=sample_player.id,
        cluster_id=sample_cluster.id,
        owned_by_server=sample_server.id,
        life_state="alive",
        position={"x": 100.0, "y": 50.0, "z": 200.0},
        stats_json={"health": 100, "blood": 5000},
        inventory_json={"slots": {}},
        inventory_checksum="test-checksum"
    )
    test_db.add(character)
    test_db.commit()
    test_db.refresh(character)
    return character
