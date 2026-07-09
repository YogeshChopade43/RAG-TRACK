import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from backend.app.core.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)

# Check alembic version
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM alembic_version"))
    versions = [row[0] for row in result]
    print("Alembic versions:", versions)
    
    # Check if tables exist
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    tables = [row[0] for row in result]
    print("Tables:", tables)
    
    # Set alembic version
    if '001_initial' not in versions:
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001_initial')"))
        conn.commit()
        print("Alembic version recorded")