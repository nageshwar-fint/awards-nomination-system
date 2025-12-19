# Flexible Criteria System

## Overview

The system now supports flexible, configurable criteria for nominations. HR can create criteria with different question types (text, single-select, multi-select, text with image), and Team Leads fill out nominations by answering these questions.

## Workflow

1. **HR**: Creates nomination cycle and defines criteria with JSON configuration
2. **Team Lead**: Submits nominations by answering criteria questions
3. **Manager**: Reviews nominations, discusses with team lead, rates (0-10), and approves/rejects
4. **HR**: Finalizes cycle and announces results

## Criteria Configuration

Each criteria can have a `config` field with the following structure:

### Question Types

#### 1. Text (`type: "text"`)
Simple text answer.

```json
{
  "type": "text",
  "required": true
}
```

**Answer format:**
```json
{
  "text": "The nominee demonstrates excellent leadership..."
}
```

#### 2. Single Select (`type: "single_select"`)
Choose one option from a list.

```json
{
  "type": "single_select",
  "required": true,
  "options": ["Option 1", "Option 2", "Option 3"]
}
```

**Answer format:**
```json
{
  "selected": "Option 1"
}
```

#### 3. Multi Select (`type: "multi_select"`)
Choose multiple options from a list.

```json
{
  "type": "multi_select",
  "required": true,
  "options": ["Follows best practices", "Excellent communication", "Mentors others"]
}
```

**Answer format:**
```json
{
  "selected_list": ["Follows best practices", "Mentors others"]
}
```

#### 4. Text with Image (`type: "text_with_image"`)
Text answer with optional image attachment.

```json
{
  "type": "text_with_image",
  "required": true,
  "image_required": false
}
```

**Answer format:**
```json
{
  "text": "Description of achievement",
  "image_url": "https://example.com/uploads/achievement.jpg"
}
```

## API Examples

### Create Criteria with Configuration

```bash
POST /api/v1/cycles/{cycle_id}/criteria

[
  {
    "name": "Technical Excellence",
    "weight": 0.3,
    "description": "Assess technical skills",
    "config": {
      "type": "multi_select",
      "required": true,
      "options": [
        "Follows coding standards",
        "Writes unit tests",
        "Code reviews thoroughly",
        "Documents code well"
      ]
    }
  },
  {
    "name": "Leadership",
    "weight": 0.3,
    "description": "Leadership qualities",
    "config": {
      "type": "text",
      "required": true
    }
  },
  {
    "name": "Achievement Documentation",
    "weight": 0.4,
    "description": "Document major achievements",
    "config": {
      "type": "text_with_image",
      "required": false,
      "image_required": false
    }
  }
]
```

### Submit Nomination with Answers

```bash
POST /api/v1/nominations

{
  "cycle_id": "uuid",
  "nominee_user_id": "uuid",
  "scores": [
    {
      "criteria_id": "criteria-uuid-1",
      "answer": {
        "selected_list": ["Follows coding standards", "Writes unit tests"]
      }
    },
    {
      "criteria_id": "criteria-uuid-2",
      "answer": {
        "text": "The nominee consistently demonstrates strong leadership..."
      }
    },
    {
      "criteria_id": "criteria-uuid-3",
      "answer": {
        "text": "Led the implementation of microservices architecture",
        "image_url": "https://storage.example.com/achievement.jpg"
      }
    }
  ]
}
```

### Manager Approval with Rating

```bash
POST /api/v1/approvals/approve

{
  "nomination_id": "uuid",
  "reason": "Discussed with team lead, nominee meets all criteria",
  "rating": 8.5
}
```

## Database Schema Changes

### Criteria Model
- Added `config` JSONB field for question configuration

### NominationCriteriaScore Model
- `score` field made optional (can be calculated from answer)
- Added `answer` JSONB field to store flexible answers
- `comment` field kept for backward compatibility

### Approval Model
- Added `rating` Numeric field (0-10 scale) for manager ratings

## Migration Notes

1. Existing criteria without `config` will be treated as legacy (numeric scoring)
2. Existing `score` values will be preserved
3. New nominations should use the `answer` field
4. Backward compatibility maintained for legacy scoring system

## Frontend Implementation

Frontend should:
1. Read criteria `config` to render appropriate input types
2. Validate answers based on `required` and `image_required` flags
3. Submit answers in the appropriate format for each question type
4. Display manager ratings alongside approval status
5. Handle image uploads and provide URLs for `text_with_image` type

## Scoring Calculation

For backward compatibility:
- Legacy numeric scores are still supported
- New system can calculate scores from answers if needed
- Managers provide ratings (0-10) during approval
- Final rankings use a combination of criteria weights and manager ratings
