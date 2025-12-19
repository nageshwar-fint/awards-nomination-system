from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, condecimal, conint


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, description="Initial password for the user")
    role: str
    team_id: Optional[UUID] = None
    status: Optional[str] = Field("ACTIVE", description="User status: ACTIVE or INACTIVE")


class UserUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = None
    team_id: Optional[UUID] = None
    status: Optional[str] = None


class UserRead(BaseSchema):
    id: UUID
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    role: str
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None  # Name of the team
    status: str
    profile_picture_url: Optional[str] = None
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


class CycleUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    status: Optional[str] = None


class CycleRead(CycleCreate):
    id: UUID
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class CriteriaConfig(BaseSchema):
    """Criteria question configuration."""
    type: str = Field(..., description="Question type: text, single_select, multi_select, text_with_image")
    required: bool = Field(default=True, description="Whether this question is required")
    # For select types: list of options
    options: Optional[List[str]] = Field(None, description="Options for select types")
    # For text_with_image: whether image is required
    image_required: Optional[bool] = Field(None, description="Whether image is required (for text_with_image type)")


class CriteriaCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    weight: condecimal(max_digits=5, decimal_places=2)
    description: Optional[str] = None
    is_active: bool = True
    config: Optional[dict] = Field(None, description="Question configuration (type, options, etc.)")


class CriteriaUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    weight: Optional[condecimal(max_digits=5, decimal_places=4)] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None


class CriteriaRead(CriteriaCreate):
    id: UUID
    cycle_id: UUID
    created_at: datetime
    updated_at: datetime


class NominationAnswerInput(BaseSchema):
    """Answer to a criteria question."""
    # For text type
    text: Optional[str] = None
    # For single_select type
    selected: Optional[str] = None
    # For multi_select type
    selected_list: Optional[List[str]] = None
    # For text_with_image type
    image_url: Optional[str] = Field(None, description="URL to uploaded image")


class NominationScoreInput(BaseSchema):
    """Legacy schema - kept for backward compatibility."""
    criteria_id: UUID
    score: Optional[conint(ge=1)] = None  # Made optional, can be calculated from answer
    comment: Optional[str] = None
    # New flexible answer format
    answer: Optional[NominationAnswerInput] = Field(None, description="Answer to criteria question")


class NominationCreate(BaseSchema):
    cycle_id: UUID
    nominee_user_id: UUID
    # submitted_by is taken from authenticated user, not request body
    scores: List[NominationScoreInput]


class NominationRead(BaseSchema):
    id: UUID
    cycle_id: UUID
    nominee_user_id: UUID
    nominee_name: Optional[str] = None  # Name of the nominee
    nominee_email: Optional[str] = None  # Email of the nominee
    team_id: Optional[UUID]
    submitted_by: UUID
    submitted_by_name: Optional[str] = None  # Name of the person who submitted
    submitted_by_email: Optional[str] = None  # Email of the person who submitted
    submitted_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime


class ApprovalActionRequest(BaseSchema):
    nomination_id: UUID
    # actor_user_id is taken from authenticated user, not request body
    reason: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=10, description="Manager rating (0-10 scale)")


class ApprovalRead(BaseSchema):
    id: UUID
    nomination_id: UUID
    actor_user_id: UUID
    action: str
    reason: Optional[str]
    rating: Optional[float] = Field(None, description="Manager rating (0-10 scale)")
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


# Authentication schemas
class SecurityQuestionInput(BaseSchema):
    question_text: str = Field(..., max_length=500)
    answer: str = Field(..., min_length=1)  # Will be hashed before storage


class RegisterRequest(BaseSchema):
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    team_id: Optional[UUID] = None
    security_questions: List[SecurityQuestionInput] = Field(..., min_length=2, max_length=5)  # Require 2-5 security questions


class LoginRequest(BaseSchema):
    email: str = Field(..., max_length=255)
    password: str


class ForgotPasswordRequest(BaseSchema):
    email: str = Field(..., max_length=255)


class SecurityQuestionAnswer(BaseSchema):
    question_text: str = Field(..., max_length=500)
    answer: str = Field(..., min_length=1)


class ResetPasswordRequest(BaseSchema):
    email: str = Field(..., max_length=255)
    security_question_answers: List[SecurityQuestionAnswer] = Field(..., min_length=2)  # Must answer all security questions
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserRead"


class MessageResponse(BaseSchema):
    message: str
