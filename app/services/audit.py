from uuid import UUID
from typing import Any, Optional

from sqlalchemy.orm import Session

from app import models


def record_audit(
    session: Session,
    actor_user_id: Optional[UUID],
    action: str,
    entity_type: str,
    entity_id: Optional[UUID],
    payload: Optional[dict[str, Any]] = None,
) -> models.AuditLog:
    audit = models.AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    session.add(audit)
    session.flush()
    return audit
