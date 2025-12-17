from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, condecimal, conint


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    role: str
    team_id: Optional[UUID] = None


class UserRead(UserCreate):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class TeamCreate(BaseSchema):
    name: str = Field(..., max_length=255)


class TeamRead(TeamCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class CycleCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    start_at: datetime
    end_at: datetime
    created_by: UUID


class CycleRead(CycleCreate):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class CriteriaCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    weight: condecimal(max_digits=5, decimal_places=4)
    description: Optional[str] = None
    is_active: bool = True


class CriteriaRead(CriteriaCreate):
    id: UUID
    cycle_id: UUID
    created_at: datetime
    updated_at: datetime


class NominationScoreInput(BaseSchema):
    criteria_id: UUID
    score: conint(ge=1)
    comment: Optional[str] = None


class NominationCreate(BaseSchema):
    cycle_id: UUID
    nominee_user_id: UUID
    submitted_by: UUID
    scores: List[NominationScoreInput]


class NominationRead(BaseSchema):
    id: UUID
    cycle_id: UUID
    nominee_user_id: UUID
    team_id: Optional[UUID]
    submitted_by: UUID
    submitted_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime


class ApprovalActionRequest(BaseSchema):
    nomination_id: UUID
    actor_user_id: UUID
    reason: Optional[str] = None


class ApprovalRead(BaseSchema):
    id: UUID
    nomination_id: UUID
    actor_user_id: UUID
    action: str
    reason: Optional[str]
    acted_at: datetime
    created_at: datetime
    updated_at: datetime


class AuditLogRead(BaseSchema):
    id: UUID
    actor_user_id: Optional[UUID]
    action: str
    entity_type: str
    entity_id: Optional[UUID]
    payload: Optional[dict]
    created_at: datetime
    updated_at: datetime


class RankingRead(BaseSchema):
    id: UUID
    cycle_id: UUID
    team_id: Optional[UUID]
    nominee_user_id: UUID
    total_score: condecimal(max_digits=10, decimal_places=4)
    rank: int
    computed_at: datetime
    created_at: datetime
    updated_at: datetime


class RankingHistoryRead(BaseSchema):
    id: UUID
    source_ranking_id: UUID
    cycle_id: UUID
    team_id: Optional[UUID]
    nominee_user_id: UUID
    total_score: condecimal(max_digits=10, decimal_places=4)
    rank: int
    computed_at: datetime
    created_at: datetime
    updated_at: datetime


class FinalizeResult(BaseSchema):
    cycle_id: UUID
    rankings_created: int
    nominations_snapshotted: int
