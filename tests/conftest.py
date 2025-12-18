import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_session
from app.auth.jwt import JWTPayload
from app.models.domain import User, UserRole, Team, NominationCycle, CycleStatus, Criteria, Nomination, NominationStatus


# Test database setup
# Using SQLite for tests - need to handle PostgreSQL-specific types
from sqlalchemy import event
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,  # Set to True for SQL debugging
)

# Map PostgreSQL JSONB to SQLite JSON
@event.listens_for(engine, "connect", insert=True)
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better compatibility."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import TypeDecorator, Text
    import json
    
    # Create a JSONB type that works with SQLite
    class JSONBType(TypeDecorator):
        impl = Text
        cache_ok = True
        
        def load_dialect_impl(self, dialect):
            if dialect.name == 'postgresql':
                return dialect.type_descriptor(JSONB())
            else:
                return dialect.type_descriptor(Text())
        
        def process_bind_param(self, value, dialect):
            if value is not None:
                if dialect.name == 'postgresql':
                    return value
                else:
                    return json.dumps(value) if not isinstance(value, str) else value
            return value
        
        def process_result_value(self, value, dialect):
            if value is not None:
                if dialect.name == 'postgresql':
                    return value
                else:
                    return json.loads(value) if isinstance(value, str) else value
            return value
    
    # Replace JSONB with JSONBType in metadata before creating tables (only once)
    # Store original types to restore later if needed
    jsonb_columns = {}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB) and column not in jsonb_columns:
                jsonb_columns[column] = column.type
                column.type = JSONBType()
    
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        # Restore original JSONB types
        for column, original_type in jsonb_columns.items():
            column.type = original_type


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""
    def override_get_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# Test data fixtures
@pytest.fixture
def test_team(db_session: Session) -> Team:
    """Create a test team."""
    team = Team(id=uuid4(), name="Engineering Team")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture
def test_employee_user(db_session: Session, test_team: Team) -> User:
    """Create a test employee user."""
    user = User(
        id=uuid4(),
        name="Employee User",
        email="employee@test.com",
        role=UserRole.EMPLOYEE,
        team_id=test_team.id,
        status="ACTIVE",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_team_lead_user(db_session: Session, test_team: Team) -> User:
    """Create a test team lead user."""
    user = User(
        id=uuid4(),
        name="Team Lead User",
        email="teamlead@test.com",
        role=UserRole.TEAM_LEAD,
        team_id=test_team.id,
        status="ACTIVE",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_manager_user(db_session: Session, test_team: Team) -> User:
    """Create a test manager user."""
    user = User(
        id=uuid4(),
        name="Manager User",
        email="manager@test.com",
        role=UserRole.MANAGER,
        team_id=test_team.id,
        status="ACTIVE",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_hr_user(db_session: Session, test_team: Team) -> User:
    """Create a test HR user."""
    user = User(
        id=uuid4(),
        name="HR User",
        email="hr@test.com",
        role=UserRole.HR,
        team_id=test_team.id,
        status="ACTIVE",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_cycle(db_session: Session, test_team_lead_user: User) -> NominationCycle:
    """Create a test nomination cycle."""
    cycle = NominationCycle(
        id=uuid4(),
        name="Q1 2024 Awards",
        start_at=datetime.now(timezone.utc) - timedelta(days=30),
        end_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=CycleStatus.OPEN,
        created_by=test_team_lead_user.id,
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


@pytest.fixture
def test_draft_cycle(db_session: Session, test_team_lead_user: User) -> NominationCycle:
    """Create a test draft nomination cycle."""
    cycle = NominationCycle(
        id=uuid4(),
        name="Q2 2024 Awards Draft",
        start_at=datetime.now(timezone.utc) + timedelta(days=30),
        end_at=datetime.now(timezone.utc) + timedelta(days=60),
        status=CycleStatus.DRAFT,
        created_by=test_team_lead_user.id,
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


@pytest.fixture
def test_criteria(db_session: Session, test_cycle: NominationCycle) -> Criteria:
    """Create test criteria."""
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Leadership",
        weight=0.5,
        description="Leadership skills",
        is_active=True,
    )
    db_session.add(criteria)
    db_session.commit()
    db_session.refresh(criteria)
    return criteria


@pytest.fixture
def test_nomination(db_session: Session, test_cycle: NominationCycle, test_employee_user: User, test_team_lead_user: User, test_criteria: Criteria) -> Nomination:
    """Create a test nomination."""
    from app.models.domain import NominationCriteriaScore
    
    nomination = Nomination(
        id=uuid4(),
        cycle_id=test_cycle.id,
        nominee_user_id=test_employee_user.id,
        team_id=test_employee_user.team_id,
        submitted_by=test_team_lead_user.id,
        submitted_at=datetime.now(timezone.utc),
        status=NominationStatus.PENDING,
    )
    db_session.add(nomination)
    db_session.flush()

    score = NominationCriteriaScore(
        id=uuid4(),
        nomination_id=nomination.id,
        criteria_id=test_criteria.id,
        score=8,
        comment="Great leadership",
    )
    db_session.add(score)
    db_session.commit()
    db_session.refresh(nomination)
    return nomination


def create_jwt_token(user_id: UUID, email: str, role: str) -> str:
    """Create a JWT token for testing."""
    return JWTPayload.create_token(user_id, email, role)


@pytest.fixture
def get_auth_headers():
    """Fixture that returns a function to get auth headers for a user."""
    def _get_auth_headers(user: User) -> dict:
        token = create_jwt_token(user.id, user.email, user.role.value)
        return {"Authorization": f"Bearer {token}"}
    return _get_auth_headers
