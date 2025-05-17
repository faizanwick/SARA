from database import SessionLocal

try:
    db = SessionLocal()
    print("✅ PostgreSQL connection successful!")
except Exception as e:
    print("❌ Connection failed:", e)
finally:
    db.close()
