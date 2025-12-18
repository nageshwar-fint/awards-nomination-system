# Frontend Development Guide

Quick start guide for frontend developers integrating with the Awards Nomination System API.

## Quick Start

### 1. API Base URL

```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

### 2. Authentication Helper

```javascript
// Helper function to make authenticated requests
async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem('jwt_token'); // Or use your token storage
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Request failed');
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}
```

### 3. TypeScript Interfaces (Recommended)

```typescript
// types/api.ts

export interface Cycle {
  id: string;
  name: string;
  start_at: string; // ISO 8601
  end_at: string;   // ISO 8601
  status: 'DRAFT' | 'OPEN' | 'CLOSED' | 'FINALIZED';
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Criteria {
  id: string;
  cycle_id: string;
  name: string;
  weight: number;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Nomination {
  id: string;
  cycle_id: string;
  nominee_user_id: string;
  team_id?: string;
  submitted_by: string;
  submitted_at: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: string;
  updated_at: string;
}

export interface NominationScoreInput {
  criteria_id: string;
  score: number; // typically 1-10
  comment?: string;
}

export interface Approval {
  id: string;
  nomination_id: string;
  actor_user_id: string;
  action: 'APPROVE' | 'REJECT';
  reason?: string;
  acted_at: string;
  created_at: string;
  updated_at: string;
}

export interface Ranking {
  id: string;
  cycle_id: string;
  team_id?: string;
  nominee_user_id: string;
  total_score: number;
  rank: number;
  computed_at: string;
  created_at: string;
  updated_at: string;
}

export interface ApiError {
  error: {
    message: string;
    type: string;
    details: Record<string, any>;
  };
  request_id: string;
}
```

## Common Patterns

### Fetching Data

```typescript
// Get all cycles
const cycles: Cycle[] = await apiRequest('/cycles');

// Get specific cycle
const cycle: Cycle = await apiRequest(`/cycles/${cycleId}`);

// Get nominations with filters
const nominations: Nomination[] = await apiRequest(
  `/nominations?cycle_id=${cycleId}&status_filter=PENDING&limit=50`
);
```

### Creating Resources

```typescript
// Create cycle
const newCycle: Cycle = await apiRequest('/cycles', {
  method: 'POST',
  body: JSON.stringify({
    name: 'Q1 2024 Awards',
    start_at: '2024-01-01T00:00:00Z',
    end_at: '2024-03-31T23:59:59Z',
    created_by: 'user-id' // ignored by API
  })
});

// Submit nomination
const nomination: Nomination = await apiRequest('/nominations', {
  method: 'POST',
  body: JSON.stringify({
    cycle_id: cycleId,
    nominee_user_id: nomineeId,
    submitted_by: submitterId, // ignored by API
    scores: [
      { criteria_id: 'criteria-1', score: 8, comment: 'Great work' },
      { criteria_id: 'criteria-2', score: 9 }
    ]
  })
});
```

### Updating Resources

```typescript
// Update cycle
const updatedCycle: Cycle = await apiRequest(`/cycles/${cycleId}`, {
  method: 'PATCH',
  body: JSON.stringify({
    name: 'Updated Name',
    status: 'OPEN'
  })
});

// Update criteria
const updatedCriteria: Criteria = await apiRequest(`/criteria/${criteriaId}`, {
  method: 'PATCH',
  body: JSON.stringify({
    description: 'Updated description',
    is_active: false
  })
});
```

### Deleting Resources

```typescript
// Delete cycle
await apiRequest(`/cycles/${cycleId}`, {
  method: 'DELETE'
});

// Delete criteria
await apiRequest(`/criteria/${criteriaId}`, {
  method: 'DELETE'
});
```

## Error Handling

```typescript
try {
  const data = await apiRequest('/nominations', {
    method: 'POST',
    body: JSON.stringify(nominationData)
  });
  // Handle success
} catch (error) {
  if (error.message.includes('Cycle not open')) {
    // Show user-friendly message
    showError('This cycle is not currently accepting nominations');
  } else if (error.message.includes('Duplicate nomination')) {
    showError('You have already submitted a nomination for this person in this cycle');
  } else {
    showError('An error occurred. Please try again.');
  }
}
```

## React Example

```typescript
// hooks/useCycles.ts
import { useState, useEffect } from 'react';
import { Cycle } from '../types/api';

export function useCycles() {
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCycles() {
      try {
        setLoading(true);
        const data = await apiRequest('/cycles');
        setCycles(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch cycles');
      } finally {
        setLoading(false);
      }
    }

    fetchCycles();
  }, []);

  return { cycles, loading, error };
}

// Component
function CyclesList() {
  const { cycles, loading, error } = useCycles();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <ul>
      {cycles.map(cycle => (
        <li key={cycle.id}>
          {cycle.name} - {cycle.status}
        </li>
      ))}
    </ul>
  );
}
```

## Status Flow Diagrams

### Cycle Lifecycle

```
DRAFT → OPEN → CLOSED → FINALIZED
  ↑       ↓
  └───────┘ (can update while DRAFT)
```

**Actions:**
- **DRAFT**: Can update, delete (if no nominations), add criteria
- **OPEN**: Can submit nominations, view data
- **CLOSED**: Can compute rankings, finalize
- **FINALIZED**: Read-only

### Nomination Lifecycle

```
PENDING → APPROVED
       ↘ REJECTED
```

**Actions:**
- **PENDING**: Can be approved/rejected by MANAGER+
- **APPROVED**: Included in ranking computation
- **REJECTED**: Not included in rankings

## Form Validation

### Cycle Creation Form

```typescript
const validateCycleForm = (data: {
  name: string;
  start_at: string;
  end_at: string;
}): string[] => {
  const errors: string[] = [];

  if (!data.name || data.name.trim().length === 0) {
    errors.push('Cycle name is required');
  }

  const startDate = new Date(data.start_at);
  const endDate = new Date(data.end_at);

  if (isNaN(startDate.getTime())) {
    errors.push('Invalid start date');
  }

  if (isNaN(endDate.getTime())) {
    errors.push('Invalid end date');
  }

  if (endDate <= startDate) {
    errors.push('End date must be after start date');
  }

  return errors;
};
```

### Nomination Form

```typescript
const validateNominationForm = (data: {
  cycle_id: string;
  nominee_user_id: string;
  scores: Array<{ criteria_id: string; score: number }>;
}, criteria: Criteria[]): string[] => {
  const errors: string[] = [];

  // Check all criteria have scores
  const criteriaIds = criteria.map(c => c.id);
  const scoreCriteriaIds = data.scores.map(s => s.criteria_id);
  
  criteriaIds.forEach(criteriaId => {
    if (!scoreCriteriaIds.includes(criteriaId)) {
      errors.push(`Score required for criteria: ${criteriaId}`);
    }
  });

  // Validate score ranges
  data.scores.forEach(score => {
    if (score.score < 1 || score.score > 10) {
      errors.push('Scores must be between 1 and 10');
    }
  });

  return errors;
};
```

## UI Components Checklist

### For TEAM_LEAD Role
- [ ] Cycle management (create, update, delete DRAFT cycles)
- [ ] Criteria management (add, update, delete)
- [ ] Nomination submission form
- [ ] View own nominations
- [ ] View cycles and their status

### For MANAGER Role
- [ ] All TEAM_LEAD features
- [ ] Approval/rejection interface
- [ ] View all nominations (pending, approved, rejected)
- [ ] Compute rankings
- [ ] Finalize cycles

### For HR Role
- [ ] All MANAGER features
- [ ] Full access to all data
- [ ] Reporting and analytics

### For EMPLOYEE Role
- [ ] View cycles (read-only)
- [ ] View nominations (read-only)
- [ ] View rankings (read-only)

## Testing Your Integration

1. **Use Swagger UI**: http://localhost:8000/docs
   - Test endpoints interactively
   - See exact request/response formats
   - Test authentication

2. **Check Console**: All API calls include request IDs in headers
   - `X-Request-ID`: Unique request identifier
   - `X-Trace-ID`: Tracing identifier

3. **Common Issues**:
   - **401 Unauthorized**: Token missing or expired
   - **403 Forbidden**: Insufficient role permissions
   - **400 Bad Request**: Validation error (check `error.details`)
   - **404 Not Found**: Invalid ID or endpoint

## Best Practices

1. **Token Refresh**: Implement token refresh logic before expiration (30 minutes)

2. **Caching**: Cache read-only data (cycles, criteria) to reduce API calls

3. **Optimistic Updates**: Update UI immediately, rollback on error

4. **Loading States**: Show loading indicators for async operations

5. **Error Messages**: Display user-friendly error messages from API

6. **Pagination**: Implement pagination for large lists

7. **Date Formatting**: Format dates for display (keep ISO format for API)

8. **Form Validation**: Validate client-side, but always handle server errors

## Environment Variables

If your frontend needs to know the API URL:

```javascript
// config.js
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
```

```bash
# .env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## Support

- **API Documentation**: See `API_DOCS.md` for complete endpoint reference
- **Interactive Docs**: http://localhost:8000/docs
- **Backend Team**: Contact Vamsi for API issues
