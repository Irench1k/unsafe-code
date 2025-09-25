This example moves our flask app to SQLAlchemy (PostgreSQL) database. We introduce a three layer architecture here:

1. API layer:
  - Flask routes, decorators, etc
  - Authentication, authorization, handled here, all Flask specific code goes here as well
  - Pydantic models for request and response
2. Service layer: 
  - Business logic, all the code that is not Flask specific and not related to the database
  - Internally works with ORM entities (from SQLAlchemy) and transactions
  - Accepts Pydantic models from the API layer and returns Pydantic models back
  - Passes SQLAlchemy entities to the repository layer
3. Repository layer:
  - Handles database operations
  - Only SQLAlchemy, returns ORM entities
  - Does not use Pydantic models for input/output

The migrations are handled by Alembic.