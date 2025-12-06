from sqlalchemy import text
from app.core.database import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='expenses' AND column_name='type'"))
        if not result.fetchone():
            print("Adding 'type' column to expenses table...")
            db.execute(text("ALTER TABLE expenses ADD COLUMN type VARCHAR(20) DEFAULT 'expense'"))
            db.commit()
            print("Migration successful.")
        else:
            print("Column 'type' already exists.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
