# Frontend Implementation Plan

## Overview

This document outlines the implementation plan for the frontend of the Awards Nomination System, including role-based UI components and workflows.

## Architecture Overview

### Role-Based Access Control (RBAC)

The system has 4 roles with different permissions:

| Role | Permissions |
|------|-------------|
| **EMPLOYEE** | View-only access (cycles, nominations, rankings) |
| **TEAM_LEAD** | Submit nominations |
| **MANAGER** | Submit nominations, approve/reject with ratings, compute rankings |
| **HR** | Full system access: manage cycles, criteria, users, approve, finalize |

## UI Components Structure

### 1. Authentication Components

- **LoginForm**: Email/password login
- **RegisterForm**: Registration with security questions (2-5 required)
- **ForgotPasswordForm**: Initiate password reset
- **ResetPasswordForm**: Answer security questions to reset password
- **LogoutButton**: Call logout API and clear token

### 2. Dashboard Components (Role-Based)

#### All Roles:
- **CyclesList**: Display all cycles with status badges
- **CycleCard**: Cycle summary card (name, dates, status)
- **NominationCard**: Nomination summary card
- **RankingsTable**: Display final rankings

#### Team Lead Only:
- **NominationForm**: Form to submit nominations with flexible criteria answers
- **MyNominationsList**: View submitted nominations

#### Manager Only:
- **PendingNominationsList**: List of nominations to review
- **NominationReviewCard**: Review nomination with approve/reject actions
- **RatingInput**: Rating slider/input (0-10) for approvals
- **RankingsComputeButton**: Button to compute rankings

#### HR Only:
- **CycleManagement**: Create, update, delete cycles
- **CycleForm**: Form to create/edit cycles
- **CriteriaManagement**: Create, update, delete criteria with config
- **CriteriaConfigForm**: Form to configure question types (text, select, multi-select, image)
- **UserManagement**: Admin panel for user management (from Admin API)
- **CycleFinalizeButton**: Button to finalize cycles

### 3. Flexible Criteria Components

#### Criteria Configuration (HR Only):
- **CriteriaTypeSelector**: Radio buttons for question type
- **OptionsInput**: Dynamic input for select options
- **RequiredToggle**: Toggle for required field
- **ImageRequiredToggle**: Toggle for image requirement (text_with_image type)

#### Answer Input Components (Team Lead, Manager, HR):
- **TextAnswerInput**: Textarea for text answers
- **SingleSelectAnswer**: Radio buttons or dropdown for single select
- **MultiSelectAnswer**: Checkboxes for multi-select
- **TextWithImageAnswer**: Textarea + image upload for text_with_image type
- **AnswerInputFactory**: Component that renders the appropriate input based on criteria config

### 4. Nomination Components

- **NominationForm**: Main form that renders criteria answers dynamically
- **NominationPreview**: Preview nomination before submission
- **NominationDetailView**: View full nomination with all answers

### 5. Approval Components (Manager, HR)

- **ApprovalForm**: Form with approve/reject buttons, reason textarea, rating input
- **ApprovalHistory**: Display approval history with ratings
- **ManagerRatingDisplay**: Display manager rating (0-10) with visual indicator

## Implementation Steps

### Phase 1: Authentication & Setup

1. **Set up routing and authentication state**
   - React Router setup
   - Auth context/store (JWT token management)
   - Protected route wrapper
   - Role-based route guards

2. **Implement authentication flows**
   - Login page
   - Register page with security questions (2-5)
   - Forgot password flow
   - Reset password with security questions
   - Logout functionality

### Phase 2: Core UI Components

3. **Build base components**
   - Cycle list/cards
   - Nomination cards
   - Rankings table
   - Loading states
   - Error handling components

4. **Role-based dashboard**
   - Employee dashboard (view-only)
   - Team Lead dashboard (nominations)
   - Manager dashboard (approvals + rankings)
   - HR dashboard (full management)

### Phase 3: Flexible Criteria System

5. **Criteria management (HR only)**
   - Criteria creation form with config
   - Question type selector
   - Options input for select types
   - Criteria list/edit/delete

6. **Dynamic answer inputs**
   - Factory pattern for answer components
   - Text input component
   - Single select component
   - Multi-select component
   - Text with image component
   - Image upload integration

### Phase 4: Nomination Workflow

7. **Nomination submission (Team Lead, Manager, HR)**
   - Cycle selection
   - Nominee selection
   - Dynamic criteria answer form
   - Form validation
   - Submission with error handling

8. **Nomination viewing**
   - List view with filters
   - Detail view with all answers
   - Image display for text_with_image answers

### Phase 5: Approval Workflow

9. **Approval interface (Manager, HR)**
   - Pending nominations list
   - Nomination review page
   - Approve/reject buttons
   - Rating input (0-10)
   - Reason textarea
   - Approval history display

10. **Rankings (Manager, HR)**
    - Compute rankings button
    - Rankings table display
    - Rankings by team filter

### Phase 6: HR Management

11. **Cycle management (HR only)**
    - Create cycle form
    - Edit cycle (DRAFT only)
    - Delete cycle
    - Status transitions (DRAFT → OPEN → CLOSED → FINALIZED)
    - Finalize cycle button

12. **Criteria management (HR only)**
    - Create criteria with config
    - Update criteria
    - Delete criteria
    - Validate criteria weights

13. **User management (HR only)**
    - User list with filters
    - User detail view
    - Update user (role, status, team)
    - Activate/deactivate users

## Data Flow Examples

### Submitting a Nomination

```
1. User selects cycle (must be OPEN)
2. User selects nominee
3. System fetches cycle criteria with config
4. For each criteria:
   - Check config.type
   - Render appropriate answer input component
   - Validate based on config.required
5. User fills answers
6. On submit:
   - Transform answers to API format
   - POST /api/v1/nominations
   - Handle success/error
```

### HR Creating Criteria

```
1. HR navigates to criteria management
2. Selects cycle (must be DRAFT)
3. Opens criteria creation form
4. Fills name, weight, description
5. Selects question type (text/single_select/multi_select/text_with_image)
6. If select type: add options
7. If text_with_image: set image_required
8. Set required flag
9. POST /api/v1/cycles/{cycle_id}/criteria
10. Criteria appears in list
```

### Manager Approving Nomination

```
1. Manager views pending nominations
2. Opens nomination detail
3. Reviews all criteria answers
4. Enters rating (0-10, optional)
5. Enters reason (optional)
6. Clicks approve/reject
7. POST /api/v1/approvals/approve or /approve/reject
8. Nomination status updates
```

## API Integration Guidelines

### Error Handling

```typescript
try {
  const response = await apiRequest('/cycles', { method: 'POST', body: ... });
  // Success
} catch (error) {
  if (error.message.includes('403')) {
    // Insufficient permissions - show message
  } else if (error.message.includes('400')) {
    // Validation error - show field errors
  } else {
    // Generic error
  }
}
```

### Token Management

```typescript
// Store token after login
localStorage.setItem('jwt_token', token);

// Include in requests
headers: { 'Authorization': `Bearer ${token}` }

// Clear on logout
localStorage.removeItem('jwt_token');
```

### Role-Based UI Rendering

```typescript
const userRole = getUserRole(); // From JWT token

{userRole === 'HR' && <CycleManagement />}
{['TEAM_LEAD', 'MANAGER', 'HR'].includes(userRole) && <NominationForm />}
{['MANAGER', 'HR'].includes(userRole) && <ApprovalInterface />}
```

## Key Features to Implement

### 1. Flexible Criteria Rendering

- Dynamically render input types based on `criteria.config.type`
- Validate required fields based on `criteria.config.required`
- Handle image uploads for `text_with_image` type
- Validate selected options match criteria config options

### 2. Manager Ratings

- Display rating field (0-10) in approval form
- Show ratings in approval history
- Optional: visual rating indicator (stars, bars, etc.)

### 3. Cycle Status Management

- Show status badges (DRAFT, OPEN, CLOSED, FINALIZED)
- Disable editing when cycle is not DRAFT
- Show appropriate actions based on status
- HR-only status transitions

### 4. Image Handling

- Image upload component for `text_with_image` criteria
- Image preview before upload
- Store image URL in answer
- Display images in nomination views

## Testing Checklist

- [ ] Login/register flows
- [ ] Role-based access control
- [ ] Cycle creation (HR only)
- [ ] Criteria creation with all question types (HR only)
- [ ] Nomination submission with different answer types
- [ ] Approval with ratings (Manager/HR)
- [ ] Rankings computation (Manager/HR)
- [ ] Cycle finalization (HR only)
- [ ] User management (HR only)
- [ ] Error handling and validation
- [ ] Image upload functionality

## Documentation References

- `ROLES_AND_WORKFLOWS.md` - Complete role workflows
- `FRONTEND_GUIDE.md` - API integration guide
- `FLEXIBLE_CRITERIA_SYSTEM.md` - Criteria configuration details
- `API_DOCS.md` - Complete API documentation
- `ADMIN_API.md` - Admin API documentation
