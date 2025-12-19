"""
Seed script for local/dev environments.
Run with:
    python -m scripts.seed

Environment variables:
    ADMIN_EMAIL: Admin user email (default: admin@example.com)
    ADMIN_PASSWORD: Admin user password (default: Admin123!)
    ADMIN_NAME: Admin user name (default: Admin User)
    SEED_ADMIN: Set to 'false' to skip admin seed (default: 'true')
"""
import os
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.config import get_settings
from app.models import SecurityQuestion, Team, User, UserRole


def create_admin_user(session: Session) -> User:
    """
    Create an admin user with HR role.
    
    Uses environment variables for configuration:
    - ADMIN_EMAIL: Email address (default: admin@example.com)
    - ADMIN_PASSWORD: Password (default: Admin123!)
    - ADMIN_NAME: Name (default: Admin User)
    """
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    admin_name = os.getenv("ADMIN_NAME", "Admin User")
    
    # Check if admin already exists
    existing_admin = session.scalar(select(User).where(User.email == admin_email))
    if existing_admin:
        print(f"Admin user {admin_email} already exists. Skipping admin creation.")
        return existing_admin
    
    # Hash password
    password_hash = hash_password(admin_password)
    
    # Create admin user
    admin_user = User(
        id=uuid4(),
        name=admin_name,
        email=admin_email,
        password_hash=password_hash,
        role=UserRole.HR,
        status="ACTIVE",
    )
    session.add(admin_user)
    session.flush()
    
    # Add security questions (required for password reset)
    # Default security questions for admin
    security_questions = [
        {
            "question_text": "What is your favorite color?",
            "answer": "blue",
            "order": 1,
        },
        {
            "question_text": "What city were you born in?",
            "answer": "default",
            "order": 2,
        },
    ]
    
    for sq in security_questions:
        answer_hash = hash_password(sq["answer"].lower().strip())
        security_question = SecurityQuestion(
            id=uuid4(),
            user_id=admin_user.id,
            question_text=sq["question_text"],
            answer_hash=answer_hash,
            question_order=sq["order"],
        )
        session.add(security_question)
    
    print(f"✅ Created admin user: {admin_email}")
    print(f"   Password: {admin_password}")
    print(f"   Role: HR")
    return admin_user


def create_default_teams(session: Session) -> None:
    """Create default teams if they don't exist, and update existing teams to uppercase."""
    default_teams = ["DEVELOPMENT", "TESTING", "HR", "CRM"]
    
    # First, handle duplicates: merge lowercase teams into uppercase ones
    all_teams = session.scalars(select(Team)).all()
    
    # Group teams by uppercase name
    teams_by_upper = {}
    for team in all_teams:
        upper_name = team.name.upper()
        if upper_name not in teams_by_upper:
            teams_by_upper[upper_name] = []
        teams_by_upper[upper_name].append(team)
    
    # Merge duplicates: keep uppercase, move users from lowercase to uppercase, delete lowercase
    for upper_name, team_list in teams_by_upper.items():
        if len(team_list) > 1:
            # Find uppercase team (or use first one)
            uppercase_team = None
            lowercase_teams = []
            
            for team in team_list:
                if team.name == upper_name:
                    uppercase_team = team
                else:
                    lowercase_teams.append(team)
            
            # If no uppercase exists, make the first one uppercase
            if not uppercase_team:
                uppercase_team = team_list[0]
                uppercase_team.name = upper_name
                lowercase_teams = team_list[1:]
                print(f"✅ Converting team '{team_list[0].name}' to '{upper_name}'")
            
            # Move users from lowercase teams to uppercase team and delete lowercase teams
            for lower_team in lowercase_teams:
                users_with_team = session.scalars(select(User).where(User.team_id == lower_team.id)).all()
                for user in users_with_team:
                    user.team_id = uppercase_team.id
                    print(f"   Moved user '{user.name}' from '{lower_team.name}' to '{upper_name}'")
                
                session.delete(lower_team)
                print(f"✅ Deleted duplicate team: '{lower_team.name}'")
    
    # Now update remaining teams to uppercase
    all_teams = session.scalars(select(Team)).all()
    updated_count = 0
    for team in all_teams:
        if team.name != team.name.upper():
            old_name = team.name
            team.name = team.name.upper()
            print(f"✅ Updated team: '{old_name}' -> '{team.name}'")
            updated_count += 1
    
    # Then create default teams if they don't exist
    for team_name in default_teams:
        existing_team = session.scalar(select(Team).where(Team.name == team_name))
        if not existing_team:
            team = Team(name=team_name)
            session.add(team)
            print(f"✅ Created team: {team_name}")
        else:
            print(f"⏭️  Team '{team_name}' already exists. Skipping.")
    
    session.flush()


def main() -> None:
    """Main seed function."""
    settings = get_settings()
    database_url = os.getenv("DATABASE_URL", settings.database_url)
    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        # Always create default teams
        print("\n📦 Creating default teams...")
        try:
            create_default_teams(session)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"⚠️  Failed to create teams: {e}")
        
        # Seed admin user (if enabled)
        seed_admin = os.getenv("SEED_ADMIN", "true").lower() == "true"
        if seed_admin:
            try:
                create_admin_user(session)
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"⚠️  Failed to create admin user: {e}")
        
        # Check if other users exist (skip demo data if they do)
        user_count = session.scalar(select(func.count(User.id))) or 0
        if user_count > 0 and not seed_admin:
            print("Seed skipped: users already exist.")
            return
        
        # Optional: Create demo team and users (skip if admin was just created and there are other users)
        user_count = session.scalar(select(func.count(User.id))) or 0
        if user_count == (1 if seed_admin else 0):
            print("\n📦 Creating demo data...")
            
            # Get or create demo team
            demo_team = session.scalar(select(Team).where(Team.name == "Demo Team"))
            if not demo_team:
                demo_team = Team(name="Demo Team")
                session.add(demo_team)
                session.flush()
            
            # Create demo users (without passwords - they need to register)
            demo_users = [
                User(name="Demo Manager", email="manager@example.com", role=UserRole.MANAGER, team_id=demo_team.id),
                User(name="Demo Team Lead", email="lead@example.com", role=UserRole.TEAM_LEAD, team_id=demo_team.id),
            ]
            session.add_all(demo_users)
            print("✅ Created demo team and users (these users need to register to set passwords)")
        
        session.commit()
        print("\n✅ Seed completed.")


if __name__ == "__main__":
    main()
