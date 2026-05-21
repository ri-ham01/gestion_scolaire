from app import create_app
from app.extensions import db
from sqlalchemy import text
import re

app = create_app()

with app.app_context():
    with open('schema_v2.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Remove comments
    sql = re.sub(r'--.*', '', sql)
    # Split by semicolon
    statements = sql.split(';')
    
    with db.engine.connect() as conn:
        for stmt in statements:
            if stmt.strip():
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    print(f"Error executing statement: {stmt[:50]}... \n{e}")
        conn.commit()
    print("Database updated successfully.")
