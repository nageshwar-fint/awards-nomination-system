"""
Quick script to add default teams to the database.
Run with:
    python -m scripts.add_teams
Or via Docker:
    docker compose exec api python -m scripts.add_teams
"""
import os
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Team


def add_default_teams() -> None:
    """Add default teams if they don't exist."""
    settings = get_settings()
    database_url = os.getenv("DATABASE_URL", settings.database_url)
    engine = create_engine(database_url, future=True)
    
    default_teams = ["DEVELOPMENT", "TESTING", "HR", "CRM"]
    
    with Session(engine) as session:
        print("📦 Adding default teams...")
        
        for team_name in default_teams:
            # Check if team already exists
            existing_team = session.scalar(select(Team).where(Team.name == team_name))
            if not existing_team:
                team = Team(name=team_name)
                session.add(team)
                print(f"✅ Created team: {team_name}")
            else:
                print(f"⏭️  Team '{team_name}' already exists. Skipping.")
        
        try:
            session.commit()
            print("\n✅ Teams added successfully!")
        except Exception as e:
            session.rollback()
            print(f"\n❌ Failed to add teams: {e}")
            raise


if __name__ == "__main__":
    add_default_teams()

