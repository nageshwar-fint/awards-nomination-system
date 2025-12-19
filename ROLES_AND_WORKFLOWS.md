# Roles, Responsibilities & Workflows Guide

Complete guide for frontend developers on user roles, permissions, responsibilities, and how the Awards Nomination System works.

## Table of Contents

1. [User Roles Overview](#user-roles-overview)
2. [Role Permissions Matrix](#role-permissions-matrix)
3. [Workflows by Role](#workflows-by-role)
4. [Cycle Lifecycle](#cycle-lifecycle)
5. [Nomination Workflow](#nomination-workflow)
6. [Approval Process](#approval-process)
7. [Rankings & Finalization](#rankings--finalization)
8. [Frontend Implementation Guidelines](#frontend-implementation-guidelines)

---

## User Roles Overview

The system has **4 user roles** with hierarchical permissions:

### 1. **EMPLOYEE** 👤
- **Lowest permission level**
- **Primary Purpose**: View and browse nominations, cycles, and results
- **Can**: Read-only access to all public data
- **Cannot**: Create, modify, or approve anything

### 2. **TEAM_LEAD** 👨‍💼
- **Mid-level permission**
- **Primary Purpose**: Submit nominations for team members
- **Can**: 
  - Submit nominations for team members
  - View cycles, nominations, and rankings
- **Cannot**: Create/manage cycles, manage criteria, approve nominations, or finalize cycles

### 3. **MANAGER** 👔
- **High-level permission**
- **Primary Purpose**: Oversee nominations, approve/reject, and manage rankings
- **Can**: 
  - All TEAM_LEAD permissions
  - Approve or reject nominations
  - Compute rankings for cycles
  - Finalize cycles
- **Cannot**: None (has all practical permissions)

### 4. **HR** 👥
- **Highest permission level**
- **Primary Purpose**: Full system administration and management
- **Can**: 
  - Create, update, delete, and finalize nomination cycles
  - Create, update, and delete criteria with flexible configurations
  - Everything a MANAGER can do (approve nominations, compute rankings)
  - Manage users (via Admin API)
- **Cannot**: None (full administrative access)

---

## Role Permissions Matrix

| Feature | EMPLOYEE | TEAM_LEAD | MANAGER | HR |
|---------|----------|-----------|---------|-----|
| **View Cycles** | ✅ | ✅ | ✅ | ✅ |
| **View Nominations** | ✅ | ✅ | ✅ | ✅ |
| **View Rankings** | ✅ | ✅ | ✅ | ✅ |
| **Create Cycles** | ❌ | ❌ | ❌ | ✅ |
| **Update Cycles** (DRAFT only) | ❌ | ❌ | ❌ | ✅ |
| **Delete Cycles** (DRAFT only) | ❌ | ❌ | ❌ | ✅ |
| **Close/Finalize Cycles** | ❌ | ❌ | ❌ | ✅ |
| **Manage Criteria** (Create/Update/Delete) | ❌ | ❌ | ❌ | ✅ |
| **Submit Nominations** | ❌ | ✅ | ✅ | ✅ |
| **Approve Nominations** | ❌ | ❌ | ✅ | ✅ |
| **Reject Nominations** | ❌ | ❌ | ✅ | ✅ |
| **Compute Rankings** | ❌ | ❌ | ✅ | ✅ |

---

## Workflows by Role

### EMPLOYEE Workflow

**What they can do:**
1. **Browse Cycles**: View all active and past nomination cycles
2. **View Nominations**: See nominations (who nominated whom, scores, status)
3. **View Rankings**: See final rankings for finalized cycles

**Frontend UI Elements:**
- Cycle list/grid view
- Cycle details page
- Nomination list view
- Rankings display

**API Calls:**
```typescript
// No authentication needed for read-only endpoints
GET /api/v1/cycles
GET /api/v1/cycles/{cycle_id}
GET /api/v1/nominations
GET /api/v1/cycles/{cycle_id}/rankings
```

---

### TEAM_LEAD Workflow

**Primary Responsibilities:**
1. **Submit Nominations** for team members

**Note**: Cycle creation and criteria management are now HR-only functions. Team Leads focus on submitting nominations.

**Step-by-Step Workflow:**

#### 1. Submit a Nomination

See the "Submit Nomination" section below.

---

### HR Workflow

**Primary Responsibilities:**
1. **Create and Manage Nomination Cycles**
2. **Define and Configure Evaluation Criteria** (with flexible question types)
3. **Finalize Cycles and Announce Results**
4. **Manage Users** (via Admin API)

**Step-by-Step Workflow:**

#### 1. Create a New Cycle

```typescript
// POST /api/v1/cycles
const createCycle = async (cycleData: {
  name: string;
  start_at: string; // ISO 8601
  end_at: string;   // ISO 8601
}) => {
  const response = await fetch(`${API_BASE_URL}/cycles`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(cycleData)
  });
  return response.json(); // Returns CycleRead with status: "DRAFT"
};
```

**Important Notes:**
- Cycle starts in `DRAFT` status
- **HR only** can create cycles
- `created_by` is automatically set from the authenticated user
- Cannot set dates in the past

#### 2. Define Criteria for the Cycle (with Flexible Configuration)

```typescript
// POST /api/v1/cycles/{cycle_id}/criteria
const addCriteria = async (cycleId: string, criteria: {
  name: string;
  weight: number;      // 0.0000 to 1.0000 (should sum to ~1.0 across all criteria)
  description?: string;
  is_active?: boolean; // default: true
  config?: {           // NEW: Flexible question configuration
    type: "text" | "single_select" | "multi_select" | "text_with_image";
    required?: boolean;
    options?: string[];      // For select types
    image_required?: boolean; // For text_with_image type
  };
}[]) => {
  const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}/criteria`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(criteria)
  });
  return response.json();
};
```

**Important Notes:**
- **HR only** can manage criteria
- Criteria can only be added to `DRAFT` cycles
- Weights typically sum to 1.0 (but API doesn't enforce this)
- Criteria can be updated or deleted if not yet used in nominations
- See `FLEXIBLE_CRITERIA_SYSTEM.md` for detailed configuration options

#### 3. Update Cycle Status to OPEN

```typescript
// PATCH /api/v1/cycles/{cycle_id}
const openCycle = async (cycleId: string) => {
  const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ status: 'OPEN' })
  });
  return response.json();
};
```

**Important Notes:**
- **HR only** can update cycles
- Can only update `DRAFT` cycles
- Once `OPEN`, cycles cannot be edited (only dates and status can be updated)

---

### Submit Nomination (Team Lead, Manager, HR)

**Note**: This section applies to Team Leads, Managers, and HR. They all submit nominations the same way.

```typescript
// POST /api/v1/nominations
const submitNomination = async (nomination: {
  cycle_id: string;
  nominee_user_id: string;
  scores: Array<{
    criteria_id: string;
    // Flexible answer format (based on criteria config type)
    answer?: {
      text?: string;              // For text type
      selected?: string;          // For single_select type
      selected_list?: string[];   // For multi_select type
      image_url?: string;         // For text_with_image type
    };
    // Legacy format (backward compatibility)
    score?: number;      // 1-10 typically
    comment?: string;
  }>;
}) => {
  const response = await fetch(`${API_BASE_URL}/nominations`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(nomination)
  });
  return response.json(); // Returns NominationRead with status: "PENDING"
};
```

**Important Notes:**
- `submitted_by` is automatically set from authenticated user
- Can only submit to `OPEN` cycles
- Must provide answers for all active criteria (based on criteria config type)
- Cycle must be within `start_at` and `end_at` date range
- Answers should match the criteria question type (text, select, etc.)

**What TEAM_LEAD Cannot Do:**
- ❌ Create/update/delete cycles
- ❌ Create/update/delete criteria
- ❌ Approve/reject nominations
- ❌ Compute rankings
- ❌ Finalize cycles

---

### MANAGER Workflow

**Primary Responsibilities:**
1. **Submit Nominations** (same as Team Lead)
2. **Approve/Reject Nominations** (with optional ratings)
3. **Compute Rankings**
4. **Cannot**: Create/manage cycles, manage criteria, or finalize cycles (HR only)

#### 1. Review Pending Nominations

```typescript
// GET /api/v1/nominations?status_filter=PENDING
const getPendingNominations = async (cycleId?: string) => {
  const url = new URL(`${API_BASE_URL}/nominations`);
  url.searchParams.append('status_filter', 'PENDING');
  if (cycleId) url.searchParams.append('cycle_id', cycleId);
  
  const response = await fetch(url.toString(), {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

#### 2. Approve a Nomination (with Optional Rating)

```typescript
// POST /api/v1/approvals/approve
const approveNomination = async (
  nominationId: string, 
  reason?: string,
  rating?: number // 0-10 scale, optional
) => {
  const response = await fetch(`${API_BASE_URL}/approvals/approve`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      nomination_id: nominationId,
      reason: reason, // Optional
      rating: rating  // Optional: 0-10 scale
    })
  });
  return response.json();
};
```

#### 3. Reject a Nomination (with Optional Rating)

```typescript
// POST /api/v1/approvals/reject
const rejectNomination = async (
  nominationId: string, 
  reason?: string,
  rating?: number // 0-10 scale, optional
) => {
  const response = await fetch(`${API_BASE_URL}/approvals/reject`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      nomination_id: nominationId,
      reason: reason, // Optional but recommended
      rating: rating  // Optional: 0-10 scale
    })
  });
  return response.json();
};
```

**Important Notes:**
- Only `PENDING` nominations can be approved/rejected
- `actor_user_id` is automatically set from authenticated user
- Reason is optional but recommended for audit trail
- Rating (0-10) is optional and can be used for evaluation purposes

#### 4. Compute Rankings (After Cycle Closes)

```typescript
// POST /api/v1/cycles/{cycle_id}/rankings/compute
const computeRankings = async (cycleId: string) => {
  const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}/rankings/compute`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json(); // Returns array of RankingRead
};
```

**Important Notes:**
- Only computes rankings for `APPROVED` nominations
- Rankings are calculated using weighted scores
- Can be recomputed multiple times (overwrites previous rankings)
- Cycle should be in `CLOSED` status (or at least past `end_at`)

#### 5. Compute Rankings (Optional - Manager can do this)

```typescript
// POST /api/v1/cycles/{cycle_id}/rankings/compute
const computeRankings = async (cycleId: string) => {
  const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}/rankings/compute`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};
```

**Note:** Managers can compute rankings, but HR must finalize the cycle.

---

### HR Workflow (Continued)

#### 5. Finalize a Cycle (HR Only)

```typescript
// POST /api/v1/cycles/{cycle_id}/finalize
const finalizeCycle = async (cycleId: string) => {
  const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}/finalize`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};
```

**Important Notes:**
- Sets cycle status to `FINALIZED`
- Creates snapshots of nominations and rankings
- Cycle becomes read-only after finalization
- Should only be done after all approvals and rankings are complete
- **HR only** - Managers cannot finalize cycles

---

### HR Workflow

**Primary Responsibilities:**
1. **Create and Manage Nomination Cycles** (Create, Update, Delete, Finalize)
2. **Define and Configure Criteria** (with flexible question types)
3. **Approve/Reject Nominations** (same as Manager)
4. **Compute Rankings** (same as Manager)
5. **Manage Users** (via Admin API)

**See "HR Workflow" section above for detailed cycle and criteria management steps.**

---

## Cycle Lifecycle

Understanding the cycle status transitions is crucial for frontend developers:

### Status States

```
DRAFT → OPEN → CLOSED → FINALIZED
  ↑       ↓       ↓          ↓
  └───────┴───────┴──────────┘
         (One-way flow)
```

### Status Details

| Status | Description | Who Can Modify | Key Restrictions |
|--------|-------------|----------------|------------------|
| **DRAFT** | Initial state after creation | HR only | Can be edited, deleted, criteria can be added |
| **OPEN** | Cycle is accepting nominations | HR only | Can only change dates, no edits to criteria |
| **CLOSED** | Cycle is past end date | HR only | Read-only, no nominations accepted |
| **FINALIZED** | Cycle is complete and locked | HR only | Read-only, historical snapshot created |

### Status Transition Rules

1. **DRAFT → OPEN**: 
   - Update cycle with `status: "OPEN"`
   - Must have valid dates (`start_at <= end_at`)
   - Should have criteria defined

2. **OPEN → CLOSED**:
   - Automatic when `end_at` date passes
   - Or manual via status update (if allowed by business logic)

3. **CLOSED → FINALIZED**:
   - Only via `/finalize` endpoint
   - Requires HR role
   - Creates historical snapshots

**Frontend Implementation:**

```typescript
// Helper to check what actions are available based on cycle status
const getAvailableActions = (cycle: Cycle, userRole: UserRole) => {
  const actions = [];
  
  if (cycle.status === 'DRAFT' && ['TEAM_LEAD', 'MANAGER', 'HR'].includes(userRole)) {
    actions.push('EDIT', 'DELETE', 'ADD_CRITERIA', 'OPEN');
  }
  
  if (cycle.status === 'OPEN' && ['TEAM_LEAD', 'MANAGER', 'HR'].includes(userRole)) {
    actions.push('SUBMIT_NOMINATION');
    // Dates can still be updated
    actions.push('UPDATE_DATES');
  }
  
  if (cycle.status === 'CLOSED' && ['MANAGER', 'HR'].includes(userRole)) {
    actions.push('COMPUTE_RANKINGS', 'FINALIZE');
  }
  
  if (cycle.status === 'FINALIZED') {
    // Read-only, no actions available
  }
  
  return actions;
};
```

---

## Nomination Workflow

### Nomination Status Flow

```
PENDING → APPROVED
    ↓
  REJECTED
```

### Nomination Lifecycle

1. **Submission (PENDING)**
   - TEAM_LEAD+ submits nomination
   - Status: `PENDING`
   - Includes scores for all criteria

2. **Review (PENDING)**
   - MANAGER+ can view pending nominations
   - Can see scores, comments, nominee details

3. **Decision (APPROVED/REJECTED)**
   - MANAGER+ approves or rejects
   - Optional reason provided
   - Status changes accordingly

4. **Ranking (APPROVED only)**
   - Only `APPROVED` nominations are included in rankings
   - `REJECTED` nominations are excluded

**Frontend Implementation:**

```typescript
// Get nominations by status
const getNominationsByStatus = async (
  status: 'PENDING' | 'APPROVED' | 'REJECTED',
  cycleId?: string
) => {
  const url = new URL(`${API_BASE_URL}/nominations`);
  url.searchParams.append('status_filter', status);
  if (cycleId) url.searchParams.append('cycle_id', cycleId);
  
  const response = await fetch(url.toString(), {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Check if user can approve/reject
const canApproveReject = (nomination: Nomination, userRole: UserRole) => {
  return nomination.status === 'PENDING' && 
         ['MANAGER', 'HR'].includes(userRole);
};
```

---

## Approval Process

### Approval Workflow

1. **Nomination is Submitted** → Status: `PENDING`
2. **Manager Reviews** → Views nomination details, scores, comments
3. **Manager Decides**:
   - **Approve** → Status: `APPROVED` → Eligible for rankings
   - **Reject** → Status: `REJECTED` → Excluded from rankings

### Multiple Approvals

- A nomination can have multiple approvals (multiple managers can approve)
- Each approval creates an `Approval` record
- Nominations are `APPROVED` if at least one approval exists

**Viewing Approval History:**

```typescript
// GET /api/v1/nominations/{nomination_id}/approvals
const getApprovalHistory = async (nominationId: string) => {
  const response = await fetch(
    `${API_BASE_URL}/nominations/${nominationId}/approvals`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  return response.json();
};
```

---

## Rankings & Finalization

### Rankings Computation

**When to Compute:**
- After cycle is `CLOSED` (past `end_at` date)
- After all nominations are reviewed (APPROVED/REJECTED)
- Before finalizing the cycle

**How Rankings Work:**
1. System collects all `APPROVED` nominations for the cycle
2. For each nominee, calculates weighted total score:
   ```
   total_score = Σ (criteria_score × criteria_weight)
   ```
3. Ranks nominees by total score (highest first)
4. Assigns rank numbers (1st, 2nd, 3rd, etc.)

**Frontend Implementation:**

```typescript
// Compute rankings (MANAGER+ only)
const computeRankings = async (cycleId: string) => {
  const response = await fetch(
    `${API_BASE_URL}/cycles/${cycleId}/rankings/compute`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Failed to compute rankings');
  }
  return response.json(); // Array of RankingRead
};

// View rankings
const getRankings = async (cycleId: string) => {
  const response = await fetch(
    `${API_BASE_URL}/cycles/${cycleId}/rankings`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  return response.json();
};
```

### Finalization

**What Happens When Finalized:**
1. Cycle status changes to `FINALIZED`
2. Historical snapshots are created:
   - Nominations snapshot
   - Rankings snapshot
3. Cycle becomes read-only
4. Results are locked for historical record

**Important Notes:**
- Finalization is irreversible
- Should only be done after:
  - All nominations are reviewed
  - Rankings are computed
  - Results are verified

---

## Frontend Implementation Guidelines

### 1. Role-Based UI Rendering

```typescript
// Check user role from JWT token
const getUserRole = (): UserRole => {
  const token = localStorage.getItem('jwt_token');
  if (!token) return null;
  
  const payload = JSON.parse(atob(token.split('.')[1]));
  return payload.role as UserRole;
};

// Conditional rendering based on role
const CycleManagementButton = ({ cycle }: { cycle: Cycle }) => {
  const userRole = getUserRole();
  const canEdit = cycle.status === 'DRAFT' && 
                  ['TEAM_LEAD', 'MANAGER', 'HR'].includes(userRole);
  
  if (!canEdit) return null;
  
  return <button onClick={() => editCycle(cycle.id)}>Edit Cycle</button>;
};
```

### 2. Error Handling

```typescript
// Handle 403 Forbidden (insufficient permissions)
const handleApiError = async (response: Response) => {
  if (response.status === 403) {
    const error = await response.json();
    throw new Error(`Access denied: ${error.error?.message || 'Insufficient permissions'}`);
  }
  
  if (response.status === 401) {
    // Token expired or invalid
    // Redirect to login
    window.location.href = '/login';
    return;
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Request failed');
  }
  
  return response.json();
};
```

### 3. Permission Checks Before Actions

```typescript
// Disable buttons/actions based on permissions
const canSubmitNomination = (cycle: Cycle, userRole: UserRole): boolean => {
  return cycle.status === 'OPEN' && 
         ['TEAM_LEAD', 'MANAGER', 'HR'].includes(userRole) &&
         new Date() >= new Date(cycle.start_at) &&
         new Date() <= new Date(cycle.end_at);
};

const canApproveNomination = (nomination: Nomination, userRole: UserRole): boolean => {
  return nomination.status === 'PENDING' && 
         ['MANAGER', 'HR'].includes(userRole);
};
```

### 4. Status Badge Components

```typescript
// Cycle Status Badge
const CycleStatusBadge = ({ status }: { status: CycleStatus }) => {
  const colors = {
    DRAFT: 'gray',
    OPEN: 'green',
    CLOSED: 'orange',
    FINALIZED: 'blue'
  };
  
  return (
    <span className={`badge badge-${colors[status]}`}>
      {status}
    </span>
  );
};

// Nomination Status Badge
const NominationStatusBadge = ({ status }: { status: NominationStatus }) => {
  const colors = {
    PENDING: 'yellow',
    APPROVED: 'green',
    REJECTED: 'red'
  };
  
  return (
    <span className={`badge badge-${colors[status]}`}>
      {status}
    </span>
  );
};
```

### 5. Form Validation

```typescript
// Validate cycle dates
const validateCycleDates = (startAt: string, endAt: string): string | null => {
  const start = new Date(startAt);
  const end = new Date(endAt);
  const now = new Date();
  
  if (start >= end) {
    return 'End date must be after start date';
  }
  
  if (start < now) {
    return 'Start date cannot be in the past';
  }
  
  return null;
};

// Validate nomination scores
const validateNominationScores = (
  scores: Array<{ criteria_id: string; score: number }>,
  criteria: Criteria[]
): string | null => {
  const activeCriteria = criteria.filter(c => c.is_active);
  
  if (scores.length !== activeCriteria.length) {
    return 'Must provide scores for all active criteria';
  }
  
  const scoreRange = scores.every(s => s.score >= 1 && s.score <= 10);
  if (!scoreRange) {
    return 'Scores must be between 1 and 10';
  }
  
  return null;
};
```

---

## Quick Reference: Who Can Do What

### Creating Content
- **Create Cycle**: TEAM_LEAD, MANAGER, HR
- **Add Criteria**: TEAM_LEAD, MANAGER, HR (DRAFT cycles only)
- **Submit Nomination**: TEAM_LEAD, MANAGER, HR (OPEN cycles only)

### Modifying Content
- **Update Cycle**: TEAM_LEAD, MANAGER, HR (DRAFT only)
- **Update Criteria**: TEAM_LEAD, MANAGER, HR (DRAFT cycles, unused criteria only)
- **Delete Cycle**: TEAM_LEAD, MANAGER, HR (DRAFT, no nominations)

### Approvals
- **Approve Nomination**: MANAGER, HR
- **Reject Nomination**: MANAGER, HR

### Rankings & Finalization
- **Compute Rankings**: MANAGER, HR
- **Finalize Cycle**: MANAGER, HR

### Viewing
- **View Everything**: All roles (EMPLOYEE, TEAM_LEAD, MANAGER, HR)

---

## Best Practices

1. **Always check user role before showing action buttons**
2. **Validate data client-side before sending to API**
3. **Handle 403 errors gracefully (show friendly message)**
4. **Refresh data after mutations (POST/PATCH/DELETE)**
5. **Show loading states during async operations**
6. **Use optimistic updates where appropriate**
7. **Implement proper error boundaries**
8. **Cache user role from JWT to avoid repeated API calls**
9. **Show status badges clearly**
10. **Disable actions that are not available based on status/role**

---

## Summary

This system follows a **role-based hierarchy** where:
- **EMPLOYEE** = Read-only viewer
- **TEAM_LEAD** = Content creator (cycles, nominations)
- **MANAGER** = Content creator + Approver + Ranker
- **HR** = Full access (same as MANAGER)

The workflow flows: **Create Cycle → Define Criteria → Open Cycle → Submit Nominations → Approve/Reject → Compute Rankings → Finalize**

Always check permissions on the frontend before showing actions, but **never trust client-side checks alone** - the API enforces permissions server-side.
