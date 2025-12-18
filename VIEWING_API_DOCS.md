# Viewing API Documentation and Schema

FastAPI automatically generates interactive API documentation. Here's how to access it:

## Web Interface (Interactive)

### 1. Swagger UI (Recommended)

Open in your browser:
```
http://localhost:8000/docs
```

Features:
- ✅ Interactive API explorer
- ✅ Try out endpoints directly
- ✅ See request/response schemas
- ✅ Authentication support (click "Authorize" button)

### 2. ReDoc (Alternative)

Open in your browser:
```
http://localhost:8000/redoc
```

Features:
- 📖 Clean, readable documentation format
- 📋 Better for printing/sharing
- 🔍 Search functionality

## OpenAPI Schema (JSON)

### View Raw OpenAPI Schema

```bash
# Using curl
curl http://localhost:8000/openapi.json | jq .

# Or save to file
curl http://localhost:8000/openapi.json > openapi-schema.json
```

### Using Docker

```bash
# View schema
docker compose exec api curl http://localhost:8000/openapi.json | jq .

# Or from host machine
curl http://localhost:8000/openapi.json | jq .
```

## Schema Files in Codebase

The schemas are defined in Pydantic models:

### Request/Response Schemas
- **Location**: `app/schemas/base.py`
- Contains all Pydantic models for API requests/responses

### Database Models
- **Location**: `app/models/domain.py`
- Contains SQLAlchemy ORM models

## Quick Access Commands

```bash
# Check if API is running
curl http://localhost:8000/api/v1/health

# Open docs in browser (macOS)
open http://localhost:8000/docs

# Open ReDoc in browser (macOS)
open http://localhost:8000/redoc

# Download OpenAPI schema
curl -o openapi.json http://localhost:8000/openapi.json

# Pretty print schema (if jq is installed)
curl -s http://localhost:8000/openapi.json | jq . > openapi-pretty.json
```

## Example: View Schema for Specific Endpoint

```bash
# Get schema and filter for specific endpoint
curl -s http://localhost:8000/openapi.json | jq '.paths["/api/v1/auth/register"]'

# Get all paths
curl -s http://localhost:8000/openapi.json | jq '.paths | keys'

# Get all components/schemas
curl -s http://localhost:8000/openapi.json | jq '.components.schemas | keys'
```

## Using the Interactive Docs

### 1. Authentication

1. Go to http://localhost:8000/docs
2. Click the **"Authorize"** button (top right)
3. Enter your JWT token in the format: `Bearer <your-token>`
4. Click "Authorize"
5. Now you can test protected endpoints

### 2. Testing Endpoints

1. Find the endpoint you want to test
2. Click "Try it out"
3. Fill in request parameters
4. Click "Execute"
5. See response below

### 3. View Request/Response Schemas

- Expand any endpoint to see:
  - **Parameters**: Path, query, header parameters
  - **Request body**: Schema for POST/PUT requests
  - **Responses**: All possible response codes and schemas

## Production Notes

⚠️ **Important**: In production (`APP_ENV=production`), the docs endpoints are **disabled** for security.

The docs are only available in:
- `local` environment (default)
- `development` environment
- `staging` environment (if configured)

## Export Schema for External Tools

You can use the OpenAPI schema with:

- **Postman**: Import from OpenAPI URL
- **Insomnia**: Import OpenAPI schema
- **Swagger Editor**: Paste schema JSON
- **Code Generation**: Generate client SDKs using openapi-generator

### Example: Generate TypeScript Client

```bash
# Install openapi-generator
npm install -g @openapitools/openapi-generator-cli

# Generate TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-axios \
  -o ./generated-client
```
