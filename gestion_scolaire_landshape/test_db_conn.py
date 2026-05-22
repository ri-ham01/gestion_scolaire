import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

try:
    conn = pymysql.connect(
        host='b7z9qy.h.filess.io',
        port=61001,
        user='gestion_scolaire_landshape',
        password='a635b506c2c42970e3c7b09d88e3e7d657fca2d2',
        database='gestion_scolaire_landshape',
        connect_timeout=60
    )
    print("Connection successful!")
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("Tables:", len(tables))
    if len(tables) == 0:
        print("Database is empty!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
