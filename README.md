## Generate a migration: (Alembic reads your models and creates a script to build the tables).
- `alembic revision --autogenerate -m "Initial tables"` 
## Apply migrations: (Runs the scripts to update the database).
- `alembic upgrade head` 
## Revert a migration: (Undoes the last migration).
- `alembic downgrade -1` 
