# API Documentation for Frontend

Complete API reference for frontend integration.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All protected endpoints require JWT authentication via Bearer token in the Authorization header.

### Getting a Token

**Note:** Currently, the API doesn't have a login endpoint. Tokens need to be generated server-side or using the JWT creation utility. For development, you can use the JWT helper function in the backend.

```javascript
// Example: Include token in requests
const token = 'your-jwt-token-here';

fetch('http://localhost:8000/api/v1/cycles', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
```

### Token Format

JWT tokens contain:
- `sub`: User ID (UUID)
- `email`: User email
- `role`: User role (EMPLOYEE, TEAM_LEAD, MANAGER, HR)
- `exp`: Expiration timestamp
- `iss`: Issuer (awards-nomination-system)
- `aud`: Audience (awards-nomination-system)

**Token expires after 30 minutes** (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`).

## Roles and Permissions

| Role | Permissions |
|------|-------------|
| **EMPLOYEE** | Read-only access to cycles, nominations, rankings |
| **TEAM_LEAD** | Can submit nominations, create/update cycles (DRAFT only), manage criteria |
| **MANAGER** | All TEAM_LEAD permissions + approve/reject nominations, compute rankings, finalize cycles |
| **HR** | Full access (all MANAGER permissions) |

## Common Response Formats

### Success Response

```json
{
  "id": "uuid",
  "name": "string",
  "status": "string",
  ...
}
```

### Error Response

```json
{
  "error": {
    "message": "Error description",
    "type": "ErrorType",
    "details": {}
  },
  "request_id": "uuid"
}
```

### Pagination

Many list endpoints support pagination:

- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100, max: 1000)

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "service": "awards-nomination-system"
}
```

---

## Cycles

### List Cycles

#### GET /cycles

Get list of all nomination cycles.

**Authentication:** Optional

**Query Parameters:**
- `skip` (int, optional): Skip N records (default: 0)
- `limit` (int, optional): Limit results (default: 100, max: 1000)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "Q1 2024 Awards",
    "start_at": "2024-01-01T00:00:00Z",
    "end_at": "2024-03-31T23:59:59Z",
    "status": "OPEN",
    "created_by": "uuid",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Cycle

#### GET /cycles/{cycle_id}

Get a specific cycle by ID.

**Authentication:** Optional

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "Q1 2024 Awards",
  "start_at": "2024-01-01T00:00:00Z",
  "end_at": "2024-03-31T23:59:59Z",
  "status": "OPEN",
  "created_by": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Create Cycle

#### POST /cycles

Create a new nomination cycle.

**Authentication:** Required (TEAM_LEAD+)

**Request Body:**
```json
{
  "name": "Q2 2024 Awards",
  "start_at": "2024-04-01T00:00:00Z",
  "end_at": "2024-06-30T23:59:59Z",
  "created_by": "uuid"  // Ignored, uses authenticated user
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "Q2 2024 Awards",
  "start_at": "2024-04-01T00:00:00Z",
  "end_at": "2024-06-30T23:59:59Z",
  "status": "DRAFT",
  "created_by": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update Cycle

#### PATCH /cycles/{cycle_id}

Update a cycle (only DRAFT cycles can be updated).

**Authentication:** Required (TEAM_LEAD+)

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Name",
  "start_at": "2024-04-01T00:00:00Z",
  "end_at": "2024-06-30T23:59:59Z",
  "status": "OPEN"  // Valid values: DRAFT, OPEN, CLOSED, FINALIZED
}
```

**Response:** `200 OK` (same as Get Cycle)

**Errors:**
- `400`: Cycle is not in DRAFT status
- `400`: end_at must be after start_at

### Delete Cycle

#### DELETE /cycles/{cycle_id}

Delete a cycle (only DRAFT cycles with no nominations).

**Authentication:** Required (TEAM_LEAD+)

**Response:** `204 No Content`

**Errors:**
- `400`: Cycle is not in DRAFT status
- `400`: Cycle has existing nominations

---

## Criteria

### List Cycle Criteria

#### GET /cycles/{cycle_id}/criteria

Get criteria for a specific cycle.

**Authentication:** Optional

**Query Parameters:**
- `active_only` (boolean, optional): Filter to only active criteria (default: true)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "cycle_id": "uuid",
    "name": "Leadership",
    "weight": 0.5,
    "description": "Leadership skills",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Criteria

#### GET /criteria/{criteria_id}

Get a specific criteria by ID.

**Authentication:** Optional

**Response:** `200 OK` (same format as list item)

### Add Criteria

#### POST /cycles/{cycle_id}/criteria

Add criteria to a cycle.

**Authentication:** Required (TEAM_LEAD+)

**Request Body:**
```json
[
  {
    "name": "Leadership",
    "weight": 0.5,
    "description": "Leadership skills",
    "is_active": true
  },
  {
    "name": "Innovation",
    "weight": 0.3,
    "description": "Innovative contributions"
  }
]
```

**Response:** `201 Created`
```json
[
  {
    "id": "uuid",
    "cycle_id": "uuid",
    "name": "Leadership",
    "weight": 0.5,
    "description": "Leadership skills",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

**Note:** Total weight of all active criteria should not exceed 1.0

### Update Criteria

#### PATCH /criteria/{criteria_id}

Update criteria. Weight/name can only be updated for DRAFT cycles.

**Authentication:** Required (TEAM_LEAD+)

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Name",
  "weight": 0.6,
  "description": "Updated description",
  "is_active": false
}
```

**Response:** `200 OK` (same as Get Criteria)

**Errors:**
- `400`: Cannot update weight/name in non-DRAFT cycles
- `400`: Criteria weights exceed 1.0 for cycle

### Delete Criteria

#### DELETE /criteria/{criteria_id}

Delete criteria (only if unused).

**Authentication:** Required (TEAM_LEAD+)

**Response:** `204 No Content`

**Errors:**
- `400`: Criteria has been used in nominations (deactivate instead)

---

## Nominations

### List Nominations

#### GET /nominations

Get list of nominations with optional filtering.

**Authentication:** Optional

**Query Parameters:**
- `cycle_id` (UUID, optional): Filter by cycle
- `nominee_user_id` (UUID, optional): Filter by nominee
- `submitted_by` (UUID, optional): Filter by submitter
- `status_filter` (string, optional): Filter by status (PENDING, APPROVED, REJECTED)
- `skip` (int, optional): Skip N records (default: 0)
- `limit` (int, optional): Limit results (default: 100, max: 1000)

**Example:**
```
GET /nominations?cycle_id=abc-123&status_filter=PENDING&limit=50
```

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "cycle_id": "uuid",
    "nominee_user_id": "uuid",
    "team_id": "uuid",
    "submitted_by": "uuid",
    "submitted_at": "2024-01-15T10:30:00Z",
    "status": "PENDING",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### Get Nomination

#### GET /nominations/{nomination_id}

Get a specific nomination by ID.

**Authentication:** Optional

**Response:** `200 OK` (same format as list item)

### Submit Nomination

#### POST /nominations

Submit a new nomination.

**Authentication:** Required (TEAM_LEAD+)

**Request Body:**
```json
{
  "cycle_id": "uuid",
  "nominee_user_id": "uuid",
  "submitted_by": "uuid",  // Ignored, uses authenticated user
  "scores": [
    {
      "criteria_id": "uuid",
      "score": 8,
      "comment": "Excellent leadership demonstrated"
    },
    {
      "criteria_id": "uuid",
      "score": 9,
      "comment": "Outstanding innovation"
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "cycle_id": "uuid",
  "nominee_user_id": "uuid",
  "team_id": "uuid",
  "submitted_by": "uuid",
  "submitted_at": "2024-01-15T10:30:00Z",
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `400`: Cycle not open for submissions
- `400`: Criteria not active or not part of cycle
- `400`: Duplicate nomination for this cycle/nominee/submitter
- `403`: Only TEAM_LEAD, MANAGER, or HR can submit nominations

**Notes:**
- All criteria for the cycle must have scores
- Cycle must be OPEN and within start/end dates
- Scores should be integers (typically 1-10 scale)

---

## Approvals

### Get Nomination Approvals

#### GET /nominations/{nomination_id}/approvals

Get all approvals for a specific nomination.

**Authentication:** Optional

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "nomination_id": "uuid",
    "actor_user_id": "uuid",
    "action": "APPROVE",
    "reason": "Meets all criteria",
    "acted_at": "2024-01-16T14:20:00Z",
    "created_at": "2024-01-16T14:20:00Z",
    "updated_at": "2024-01-16T14:20:00Z"
  }
]
```

### Approve Nomination

#### POST /approvals/approve

Approve a nomination.

**Authentication:** Required (MANAGER+)

**Request Body:**
```json
{
  "nomination_id": "uuid",
  "actor_user_id": "uuid",  // Ignored, uses authenticated user
  "reason": "Meets all criteria and demonstrates excellent performance"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "nomination_id": "uuid",
  "actor_user_id": "uuid",
  "action": "APPROVE",
  "reason": "Meets all criteria",
  "acted_at": "2024-01-16T14:20:00Z",
  "created_at": "2024-01-16T14:20:00Z",
  "updated_at": "2024-01-16T14:20:00Z"
}
```

**Errors:**
- `400`: Nomination not found
- `400`: Nomination already processed
- `403`: Only MANAGER or HR can approve nominations

### Reject Nomination

#### POST /approvals/reject

Reject a nomination.

**Authentication:** Required (MANAGER+)

**Request Body:**
```json
{
  "nomination_id": "uuid",
  "actor_user_id": "uuid",  // Ignored, uses authenticated user
  "reason": "Does not meet minimum criteria"
}
```

**Response:** `201 Created` (same format as approve, with `action: "REJECT"`)

**Errors:** Same as approve

---

## Rankings

### Get Cycle Rankings

#### GET /cycles/{cycle_id}/rankings

Get rankings for a specific cycle.

**Authentication:** Optional

**Query Parameters:**
- `team_id` (UUID, optional): Filter by team
- `skip` (int, optional): Skip N records (default: 0)
- `limit` (int, optional): Limit results (default: 100, max: 1000)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "cycle_id": "uuid",
    "team_id": "uuid",
    "nominee_user_id": "uuid",
    "total_score": 8.5,
    "rank": 1,
    "computed_at": "2024-01-20T12:00:00Z",
    "created_at": "2024-01-20T12:00:00Z",
    "updated_at": "2024-01-20T12:00:00Z"
  }
]
```

### Compute Rankings

#### POST /cycles/{cycle_id}/rankings/compute

Compute rankings for a cycle (based on approved nominations).

**Authentication:** Required (MANAGER+)

**Response:** `201 Created`
```json
[
  {
    "id": "uuid",
    "cycle_id": "uuid",
    "team_id": "uuid",
    "nominee_user_id": "uuid",
    "total_score": 8.5,
    "rank": 1,
    "computed_at": "2024-01-20T12:00:00Z",
    "created_at": "2024-01-20T12:00:00Z",
    "updated_at": "2024-01-20T12:00:00Z"
  }
]
```

**Notes:**
- Only considers APPROVED nominations
- Scores are weighted by criteria weights
- Uses dense ranking (same score = same rank)

### Finalize Cycle

#### POST /cycles/{cycle_id}/finalize

Finalize a cycle (computes rankings and creates history snapshots).

**Authentication:** Required (MANAGER+)

**Response:** `200 OK`
```json
{
  "message": "Cycle finalized successfully",
  "cycle_id": "uuid"
}
```

**Errors:**
- `400`: Cycle must be CLOSED before finalization

**Notes:**
- Cycle status changes to FINALIZED
- Creates historical snapshots of nominations and rankings
- Can only be done once per cycle

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request (validation error, business rule violation) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 422 | Unprocessable Entity (validation error) |
| 500 | Internal Server Error |

## Error Handling

All errors follow this format:

```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "ErrorType",
    "details": {}
  },
  "request_id": "uuid-for-tracing"
}
```

**Common Error Types:**
- `ValidationError`: Request validation failed
- `ValueError`: Invalid business logic (e.g., cycle not open)
- `PermissionError`: Insufficient permissions
- `AppError`: Application-specific error

## Request IDs

All responses include `X-Request-ID` and `X-Trace-ID` headers for request tracing and debugging.

## Example: Complete Nomination Flow

### 1. Create a Cycle

```javascript
const response = await fetch('http://localhost:8000/api/v1/cycles', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Q1 2024 Awards',
    start_at: '2024-01-01T00:00:00Z',
    end_at: '2024-03-31T23:59:59Z',
    created_by: 'user-id' // ignored
  })
});

const cycle = await response.json();
```

### 2. Add Criteria

```javascript
await fetch(`http://localhost:8000/api/v1/cycles/${cycle.id}/criteria`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify([
    { name: 'Leadership', weight: 0.5, description: 'Leadership skills' },
    { name: 'Innovation', weight: 0.3, description: 'Innovation' },
    { name: 'Teamwork', weight: 0.2, description: 'Team collaboration' }
  ])
});
```

### 3. Open the Cycle

```javascript
await fetch(`http://localhost:8000/api/v1/cycles/${cycle.id}`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ status: 'OPEN' })
});
```

### 4. Submit Nominations

```javascript
await fetch('http://localhost:8000/api/v1/nominations', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    cycle_id: cycle.id,
    nominee_user_id: 'nominee-uuid',
    submitted_by: 'submitter-uuid', // ignored
    scores: [
      { criteria_id: 'criteria-1-uuid', score: 8, comment: 'Great leader' },
      { criteria_id: 'criteria-2-uuid', score: 9, comment: 'Very innovative' },
      { criteria_id: 'criteria-3-uuid', score: 7, comment: 'Good team player' }
    ]
  })
});
```

### 5. Approve/Reject Nominations

```javascript
// Approve
await fetch('http://localhost:8000/api/v1/approvals/approve', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    nomination_id: 'nomination-uuid',
    actor_user_id: 'manager-uuid', // ignored
    reason: 'Meets all criteria'
  })
});

// Or reject
await fetch('http://localhost:8000/api/v1/approvals/reject', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    nomination_id: 'nomination-uuid',
    actor_user_id: 'manager-uuid', // ignored
    reason: 'Does not meet minimum requirements'
  })
});
```

### 6. Compute Rankings

```javascript
const rankings = await fetch(
  `http://localhost:8000/api/v1/cycles/${cycle.id}/rankings/compute`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);
```

### 7. Close and Finalize Cycle

```javascript
// Close
await fetch(`http://localhost:8000/api/v1/cycles/${cycle.id}`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ status: 'CLOSED' })
});

// Finalize
await fetch(`http://localhost:8000/api/v1/cycles/${cycle.id}/finalize`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## Frontend Integration Tips

1. **Token Management**: Store JWT token securely (e.g., httpOnly cookies or secure storage). Refresh before expiration.

2. **Error Handling**: Always check response status and parse error messages from the `error` object.

3. **Loading States**: Use request IDs from response headers to track requests.

4. **Pagination**: Implement infinite scroll or pagination using `skip` and `limit` parameters.

5. **Form Validation**: Validate on client-side before submission, but always handle server-side validation errors.

6. **Optimistic Updates**: Update UI optimistically for better UX, but handle rollback on errors.

7. **Type Safety**: Use TypeScript interfaces matching the API schemas for type safety.

8. **Date Handling**: All dates are ISO 8601 format with timezone (UTC). Use libraries like `date-fns` or `moment.js` for parsing/formatting.

## Interactive API Documentation

For interactive exploration of the API:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide:
- Interactive API exploration
- Try-it-out functionality
- Complete request/response schemas
- Authentication testing
