# Authentication Flow Documentation

## Current Status

⚠️ **IMPORTANT**: The following authentication endpoints are **NOT currently implemented** in the API:
- User Registration
- User Login
- Forgot Password
- Reset Password

Currently, JWT tokens must be generated server-side or through a separate authentication service. Users are assumed to exist in the database and tokens are created externally.

---

## Proposed Authentication Flow

This document describes how the authentication flows **should work** if implemented.

---

## 1. User Registration Flow

### Overview
New users register with email and password, and are assigned a default role (typically EMPLOYEE).

### Flow Steps

```
1. User submits registration form
   ↓
2. Frontend sends POST /api/v1/auth/register
   ↓
3. Backend validates input and creates user
   ↓
4. Backend sends verification email (optional)
   ↓
5. User receives confirmation
   ↓
6. User can now login
```

### API Endpoint

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "password": "SecurePassword123!",
  "team_id": "optional-uuid"  // Optional
}
```

### Request Schema

```typescript
interface RegisterRequest {
  name: string;           // Required, max 255 chars
  email: string;          // Required, valid email format, unique
  password: string;       // Required, min 8 chars, complexity rules
  team_id?: string;       // Optional UUID
}
```

### Response

**Success (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "role": "EMPLOYEE",
    "status": "ACTIVE",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Error (400 Bad Request):**
```json
{
  "error": {
    "message": "Email already exists",
    "type": "ValidationError",
    "details": {
      "field": "email"
    }
  }
}
```

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

### Default Role Assignment

- New users default to `EMPLOYEE` role
- Role can be upgraded by MANAGER/HR later
- Or role can be specified during registration (if allowed by business rules)

### Validation Rules

1. Email must be unique
2. Email must be valid format
3. Password must meet complexity requirements
4. Name cannot be empty
5. Team ID (if provided) must exist

---

## 2. User Login Flow

### Overview
Users authenticate with email and password, receiving a JWT token for subsequent API calls.

### Flow Steps

```
1. User enters email and password
   ↓
2. Frontend sends POST /api/v1/auth/login
   ↓
3. Backend validates credentials
   ↓
4. Backend generates JWT token
   ↓
5. Frontend stores token
   ↓
6. Frontend uses token in Authorization header
```

### API Endpoint

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "SecurePassword123!"
}
```

### Request Schema

```typescript
interface LoginRequest {
  email: string;      // Required, valid email
  password: string;   // Required
}
```

### Response

**Success (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,  // 30 minutes in seconds
  "user": {
    "id": "uuid",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "role": "MANAGER",
    "team_id": "uuid",
    "status": "ACTIVE"
  }
}
```

**Error (401 Unauthorized):**
```json
{
  "error": {
    "message": "Invalid email or password",
    "type": "AuthenticationError"
  }
}
```

**Error (403 Forbidden - Account Inactive):**
```json
{
  "error": {
    "message": "Account is inactive. Please contact administrator.",
    "type": "AccountStatusError"
  }
}
```

### Security Considerations

1. **Rate Limiting**: Limit login attempts (e.g., 5 attempts per 15 minutes)
2. **Password Hashing**: Passwords must be hashed using bcrypt/argon2
3. **Token Expiration**: Tokens expire after 30 minutes (configurable)
4. **Account Status Check**: Reject login if user status is not "ACTIVE"
5. **Never return password in response**: Even hashed passwords should not be returned

### Frontend Implementation

```typescript
const login = async (email: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Login failed');
  }

  const data = await response.json();
  
  // Store token securely
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  // Set token expiration
  const expiresAt = Date.now() + (data.expires_in * 1000);
  localStorage.setItem('token_expires_at', expiresAt.toString());
  
  return data;
};
```

---

## 3. Forgot Password Flow

### Overview
Users request a password reset by providing their email address. A reset token is sent to their email.

### Flow Steps

```
1. User clicks "Forgot Password"
   ↓
2. User enters email address
   ↓
3. Frontend sends POST /api/v1/auth/forgot-password
   ↓
4. Backend generates reset token
   ↓
5. Backend sends email with reset link
   ↓
6. User receives email
   ↓
7. User clicks reset link (goes to Reset Password page)
```

### API Endpoint

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "john.doe@example.com"
}
```

### Request Schema

```typescript
interface ForgotPasswordRequest {
  email: string;  // Required, valid email format
}
```

### Response

**Success (200 OK) - Always returns success for security:**
```json
{
  "message": "If an account with that email exists, a password reset link has been sent."
}
```

**Note**: Always return success message even if email doesn't exist to prevent email enumeration attacks.

### Security Considerations

1. **Reset Token**: Generate secure random token (UUID or cryptographically random string)
2. **Token Expiration**: Reset tokens expire after 1 hour (configurable)
3. **Single Use**: Reset token can only be used once
4. **Rate Limiting**: Limit requests (e.g., 3 requests per hour per email)
5. **Email Enumeration Prevention**: Always return success message
6. **Token Storage**: Store reset token hash in database with expiration timestamp

### Database Schema (Proposed)

```sql
-- Password reset tokens table
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
```

### Email Template

```
Subject: Reset Your Password - Awards Nomination System

Hello {name},

You requested to reset your password. Click the link below to reset it:

{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
Awards Nomination System
```

---

## 4. Reset Password Flow

### Overview
Users use the reset token from the email to set a new password.

### Flow Steps

```
1. User clicks reset link in email
   ↓
2. Frontend extracts token from URL
   ↓
3. Frontend shows reset password form
   ↓
4. User enters new password
   ↓
5. Frontend sends POST /api/v1/auth/reset-password
   ↓
6. Backend validates token and updates password
   ↓
7. User can now login with new password
```

### API Endpoint

```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePassword123!"
}
```

### Request Schema

```typescript
interface ResetPasswordRequest {
  token: string;         // Required, reset token from email
  new_password: string;  // Required, must meet password requirements
}
```

### Response

**Success (200 OK):**
```json
{
  "message": "Password has been reset successfully. You can now login with your new password."
}
```

**Error (400 Bad Request - Invalid Token):**
```json
{
  "error": {
    "message": "Invalid or expired reset token",
    "type": "ValidationError"
  }
}
```

**Error (400 Bad Request - Token Already Used):**
```json
{
  "error": {
    "message": "This reset token has already been used",
    "type": "ValidationError"
  }
}
```

### Validation Rules

1. Token must exist and not be expired
2. Token must not have been used before
3. New password must meet password requirements
4. New password should be different from current password (optional but recommended)

### Security Considerations

1. **Token Validation**: Verify token exists, not expired, and not used
2. **Password Hashing**: Hash new password before storing
3. **Invalidate Token**: Mark token as used after successful reset
4. **Invalidate All Sessions**: Optionally invalidate all existing sessions (requires session management)
5. **Rate Limiting**: Limit reset attempts per token

---

## Complete Authentication Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOWS                      │
└─────────────────────────────────────────────────────────────┘

REGISTRATION:
User → Register Form → POST /auth/register → User Created → Can Login

LOGIN:
User → Login Form → POST /auth/login → JWT Token → Use Token in API Calls

FORGOT PASSWORD:
User → Forgot Password Form → POST /auth/forgot-password → Email Sent → Reset Link

RESET PASSWORD:
User → Reset Link → Reset Form → POST /auth/reset-password → Password Updated → Can Login

TOKEN REFRESH (Future):
User → Refresh Token → POST /auth/refresh → New Access Token
```

---

## Implementation Requirements

### 1. Database Changes

**Add password field to User model:**
```python
# app/models/domain.py
class User(TimestampedUUIDBase):
    # ... existing fields ...
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
```

**Add password reset tokens table** (see schema above)

### 2. Password Hashing

Use `bcrypt` or `argon2` for password hashing:

```python
# requirements.txt
bcrypt>=4.0.0
# or
argon2-cffi>=23.0.0
```

**Example implementation:**
```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
```

### 3. Email Service

Implement email sending (SMTP or service like SendGrid, AWS SES):

```python
# Example using SMTP
import smtplib
from email.mime.text import MIMEText

def send_password_reset_email(user_email: str, reset_token: str, user_name: str):
    # Implementation here
    pass
```

### 4. Rate Limiting

Implement rate limiting for login and password reset endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(...):
    # Implementation
    pass
```

### 5. New Endpoints

Create new authentication router:

```python
# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register")
async def register(...):
    # Implementation
    pass

@router.post("/login")
async def login(...):
    # Implementation
    pass

@router.post("/forgot-password")
async def forgot_password(...):
    # Implementation
    pass

@router.post("/reset-password")
async def reset_password(...):
    # Implementation
    pass
```

---

## Frontend Implementation Examples

### Registration Form

```typescript
const register = async (formData: {
  name: string;
  email: string;
  password: string;
  team_id?: string;
}) => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(formData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Registration failed');
  }

  return response.json();
};
```

### Login Form

```typescript
const login = async (email: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Login failed');
  }

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  return data;
};
```

### Forgot Password

```typescript
const forgotPassword = async (email: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email })
  });

  if (!response.ok) {
    throw new Error('Failed to send reset email');
  }

  return response.json();
};
```

### Reset Password

```typescript
const resetPassword = async (token: string, newPassword: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      token,
      new_password: newPassword
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Password reset failed');
  }

  return response.json();
};
```

---

## Security Best Practices

1. **Password Storage**
   - Never store plain text passwords
   - Use bcrypt or argon2 for hashing
   - Use salt rounds (minimum 12 for bcrypt)

2. **Token Security**
   - Use secure random tokens for password reset
   - Set reasonable expiration times
   - Invalidate tokens after use

3. **Rate Limiting**
   - Limit login attempts to prevent brute force
   - Limit password reset requests per email
   - Implement IP-based rate limiting

4. **Email Security**
   - Use HTTPS for reset links
   - Include expiration time in email
   - Don't reveal if email exists in system

5. **HTTPS Only**
   - All authentication endpoints must use HTTPS in production
   - Never send passwords or tokens over HTTP

6. **Input Validation**
   - Validate email format
   - Enforce password complexity
   - Sanitize all inputs

7. **Session Management**
   - Tokens should expire (30 minutes default)
   - Consider refresh tokens for long-lived sessions
   - Optionally invalidate all sessions on password reset

---

## Summary

To implement full authentication flows, you need:

1. ✅ Password field in User model
2. ✅ Password hashing utilities
3. ✅ Registration endpoint
4. ✅ Login endpoint with credential validation
5. ✅ Password reset token storage
6. ✅ Forgot password endpoint
7. ✅ Reset password endpoint
8. ✅ Email service for sending reset links
9. ✅ Rate limiting for security
10. ✅ Token expiration and validation

Currently, **none of these are implemented**. Users must be created manually, and tokens must be generated server-side.

---

## Next Steps

If you want to implement these flows:

1. **Database Migration**: Add password_hash field to users table
2. **Create Password Reset Tokens Table**: Store reset tokens
3. **Implement Password Utilities**: Hashing and verification
4. **Create Auth Router**: New router for authentication endpoints
5. **Implement Email Service**: For sending reset emails
6. **Add Rate Limiting**: Protect endpoints from abuse
7. **Update Documentation**: Reflect new endpoints
8. **Update Frontend Guide**: Include authentication examples
