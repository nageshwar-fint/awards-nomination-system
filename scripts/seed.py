"""
Seed script stub for local/dev environments.
Run with:
    python -m scripts.seed
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import DATABASE_URL
from app.models import Team, User, UserRole


def main() -> None:
    engine = create_engine(os.getenv("DATABASE_URL", DATABASE_URL), future=True)
    with Session(engine) as session:
        if session.query(User).count() > 0:
            print("Seed skipped: users already exist.")
            return

        # Minimal seed: one team and two users.
        team = Team(name="Demo Team")
        session.add(team)
        session.flush()

        users = [
            User(name="Demo Manager", email="manager@example.com", role=UserRole.MANAGER, team_id=team.id),
            User(name="Demo Team Lead", email="lead@example.com", role=UserRole.TEAM_LEAD, team_id=team.id),
        ]
        session.add_all(users)
        session.commit()
        print("Seed completed.")


if __name__ == "__main__":
    main()
