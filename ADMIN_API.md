# Admin API Documentation

Admin API endpoints for user management. All endpoints require **HR role** access.

## Base URL

All admin endpoints are prefixed with `/api/v1/admin`

## Authentication

All endpoints require:
1. Valid JWT token in `Authorization` header: `Bearer <token>`
2. User must have **HR** role

## Endpoints

### Create User

**POST** `/api/v1/admin/users`

Create a new user account. HR can create users with any role.

**Request Body:**
```json
{
  "name": "John Doe",                    // Required: string, max 255 chars
  "email": "john@example.com",           // Required: string, must be unique
  "password": "SecurePass123!",          // Required: string, min 8 chars, must meet strength requirements
  "role": "EMPLOYEE",                    // Required: one of EMPLOYEE, TEAM_LEAD, MANAGER, HR
  "team_id": "uuid-or-null",             // Optional: UUID or null
  "status": "ACTIVE"                     // Optional: ACTIVE or INACTIVE (default: ACTIVE)
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "EMPLOYEE",
  "team_id": "uuid-or-null",
  "status": "ACTIVE",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: Invalid password, email already in use, invalid role, invalid status, or team not found

**Validation:**
- Email must be unique
- Password must meet strength requirements
- Role must be valid UserRole enum value
- Status must be `ACTIVE` or `INACTIVE` (defaults to `ACTIVE`)
- Team ID must exist in database (if provided)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/users" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "role": "TEAM_LEAD",
    "team_id": "team-uuid",
    "status": "ACTIVE"
  }'
```

---

### List Users

**GET** `/api/v1/admin/users`

List all users with optional filtering.

**Query Parameters:**
- `skip` (int, default: 0): Number of records to skip
- `limit` (int, default: 100, max: 1000): Number of records to return
- `role_filter` (string, optional): Filter by role (`EMPLOYEE`, `TEAM_LEAD`, `MANAGER`, `HR`)
- `status_filter` (string, optional): Filter by status (`ACTIVE`, `INACTIVE`)
- `team_id` (UUID, optional): Filter by team ID
- `search` (string, optional): Search by name or email (case-insensitive partial match)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "EMPLOYEE",
    "team_id": "uuid-or-null",
    "status": "ACTIVE",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?role_filter=EMPLOYEE&status_filter=ACTIVE" \
  -H "Authorization: Bearer <token>"
```

---

### Get User

**GET** `/api/v1/admin/users/{user_id}`

Get a specific user by ID.

**Path Parameters:**
- `user_id` (UUID): User ID

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "EMPLOYEE",
  "team_id": "uuid-or-null",
  "status": "ACTIVE",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Error:** `404 Not Found` if user doesn't exist

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"
```

---

### Update User

**PATCH** `/api/v1/admin/users/{user_id}`

Update a user's information. All fields are optional - only provided fields will be updated.

**Path Parameters:**
- `user_id` (UUID): User ID

**Request Body:**
```json
{
  "name": "John Doe Updated",           // Optional: string, max 255 chars
  "email": "john.updated@example.com",  // Optional: string, must be unique
  "role": "TEAM_LEAD",                  // Optional: one of EMPLOYEE, TEAM_LEAD, MANAGER, HR
  "team_id": "uuid-or-null",            // Optional: UUID or null
  "status": "ACTIVE"                    // Optional: ACTIVE or INACTIVE
}
```

**Response:** `200 OK` (returns updated user)
```json
{
  "id": "uuid",
  "name": "John Doe Updated",
  "email": "john.updated@example.com",
  "role": "TEAM_LEAD",
  "team_id": "uuid",
  "status": "ACTIVE",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T01:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: Invalid role, status, email already in use, or team not found
- `404 Not Found`: User doesn't exist

**Validation:**
- Email must be unique (if provided)
- Role must be valid UserRole enum value
- Status must be `ACTIVE` or `INACTIVE`
- Team ID must exist in database (if provided)

**Example:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "MANAGER",
    "status": "ACTIVE"
  }'
```

---

### Delete User (Soft Delete)

**DELETE** `/api/v1/admin/users/{user_id}`

Deactivate a user (soft delete by setting status to INACTIVE).

**Path Parameters:**
- `user_id` (UUID): User ID

**Response:** `200 OK`
```json
{
  "message": "User user@example.com has been deactivated successfully"
}
```

**Errors:**
- `400 Bad Request`: Cannot delete your own account
- `404 Not Found`: User doesn't exist

**Note:** This performs a **soft delete** by setting the user's status to `INACTIVE`. The user record is not actually deleted to preserve data integrity.

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"
```

---

### Activate User

**POST** `/api/v1/admin/users/{user_id}/activate`

Activate a user by setting status to ACTIVE. Enables a user account that was previously deactivated.

**Path Parameters:**
- `user_id` (UUID): User ID

**Response:** `200 OK`
```json
{
  "message": "User user@example.com has been activated successfully"
}
```

**Errors:**
- `404 Not Found`: User doesn't exist

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000/activate" \
  -H "Authorization: Bearer <token>"
```

---

### Deactivate User

**POST** `/api/v1/admin/users/{user_id}/deactivate`

Deactivate a user by setting status to INACTIVE. Disables a user account. Deactivated users cannot log in.

**Path Parameters:**
- `user_id` (UUID): User ID

**Response:** `200 OK`
```json
{
  "message": "User user@example.com has been deactivated successfully"
}
```

**Errors:**
- `400 Bad Request`: Cannot deactivate your own account
- `404 Not Found`: User doesn't exist

**Note:** This is equivalent to the DELETE endpoint (soft delete) and can be reversed with the activate endpoint.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000/deactivate" \
  -H "Authorization: Bearer <token>"
```

---

## Common Use Cases

### Promote User to Team Lead

```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/{user_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "TEAM_LEAD"}'
```

### Assign User to Team

```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/{user_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"team_id": "team-uuid"}'
```

### Deactivate User

```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/users/{user_id}" \
  -H "Authorization: Bearer <token>"
```

### Search for Users

```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?search=john" \
  -H "Authorization: Bearer <token>"
```

### List All Managers

```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?role_filter=MANAGER" \
  -H "Authorization: Bearer <token>"
```

---

## Error Responses

All errors follow the standard error format:

```json
{
  "error": {
    "message": "Error description",
    "type": "ErrorType"
  }
}
```

**HTTP Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User doesn't have HR role
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server error

---

## Notes

1. **User Creation**: HR can create users with any role and set their initial password. The password must meet strength requirements.

2. **Password Management**: Password cannot be updated through the update endpoint. Use the password reset flow (`/api/v1/auth/reset-password`) or create a new user with the desired password.

2. **Soft Delete**: The delete endpoint performs a soft delete (sets status to INACTIVE) rather than hard deletion to preserve data integrity and audit trails.

3. **Self-Deletion Prevention**: Users cannot delete their own accounts through the admin API.

4. **Role Hierarchy**: The system has 4 roles:
   - `EMPLOYEE`: Basic user
   - `TEAM_LEAD`: Can create cycles and submit nominations
   - `MANAGER`: Can approve nominations and finalize cycles
   - `HR`: Full administrative access (required for admin API)

5. **Team Validation**: When updating `team_id`, the team must exist in the database. Setting `team_id` to `null` removes the user from their team.

---

## Testing in Swagger UI

1. Start the API: `docker compose up -d`
2. Open Swagger UI: http://localhost:8000/docs
3. Click "Authorize" button (top right)
4. Enter your JWT token: `Bearer <your-token>`
5. Navigate to the "admin" section
6. Try out the endpoints!
