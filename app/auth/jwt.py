from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session
from app.models.domain import User, UserRole

settings = get_settings()
security = HTTPBearer()


class JWTPayload:
    """JWT payload structure."""

    def __init__(self, user_id: UUID, email: str, role: str, exp: datetime, iss: str, aud: str):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.exp = exp
        self.iss = iss
        self.aud = aud

    @classmethod
    def from_token(cls, token: str) -> "JWTPayload":
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
            return cls(
                user_id=UUID(payload["sub"]),
                email=payload["email"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iss=payload["iss"],
                aud=payload["aud"],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @classmethod
    def create_token(cls, user_id: UUID, email: str, role: str) -> str:
        """Create a new JWT token."""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "exp": exp,
            "iat": now,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }

        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> User:
    """Dependency to get current authenticated user from JWT token."""
    token = credentials.credentials
    jwt_payload = JWTPayload.from_token(token)

    user = db.get(User, jwt_payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Optional: Verify role hasn't changed
    if user.role.value != jwt_payload.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User role has changed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_session),
) -> Optional[User]:
    """Dependency to optionally get current user (for endpoints that work with or without auth)."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
