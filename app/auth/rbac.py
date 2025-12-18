from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.auth.jwt import get_current_user
from app.models.domain import User, UserRole


class RequireRole:
    """Dependency factory for role-based access control."""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """Check if current user has one of the required roles."""
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in self.allowed_roles]}",
            )
        return current_user


# Common role dependencies
RequireTeamLead = RequireRole([UserRole.TEAM_LEAD, UserRole.MANAGER, UserRole.HR])
RequireManager = RequireRole([UserRole.MANAGER, UserRole.HR])
RequireHR = RequireRole([UserRole.HR])


def require_any_role(*roles: UserRole) -> RequireRole:
    """Create a role requirement for any of the specified roles."""
    return RequireRole(list(roles))


async def get_current_user_id(current_user: User = Depends(get_current_user)) -> UUID:
    """Dependency to get current user ID for audit context."""
    return current_user.id
