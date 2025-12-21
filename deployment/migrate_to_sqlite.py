import os
import sys
import argparse
import glob
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add root to path (one level up from this script)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
os.chdir(ROOT_DIR) # Ensure relative paths in script work correctly

from app.db.models import Expense, Base
from app.core.config import settings

def get_latest_backup():
    """Finds the latest backup folder based on the DD-MM-YYYY_HH-MM format."""
    backup_root = "backups"
    if not os.path.exists(backup_root):
        return None
    
    folders = [f for f in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, f))]
    if not folders:
        return None
    
    # Sort folders by parsing the date string
    try:
        folders.sort(key=lambda x: datetime.strptime(x, "%d-%m-%Y_%H-%M"), reverse=True)
        latest_folder = folders[0]
        dump_path = os.path.join(backup_root, latest_folder, "xpense_db_dump.sql")
        if os.path.exists(dump_path):
            return dump_path
    except ValueError:
        # Fallback to simple directory modification time if format doesn't match
        folders.sort(key=lambda x: os.path.getmtime(os.path.join(backup_root, x)), reverse=True)
        for f in folders:
            dump_path = os.path.join(backup_root, f, "xpense_db_dump.sql")
            if os.path.exists(dump_path):
                return dump_path
                
    return None

def parse_value(val, type_hint):
    if val == r"\N" or val.strip() == "":
        return None
    if type_hint == bool:
        return val.lower() in ("t", "true", "1")
    if type_hint == int:
        return int(val)
    if type_hint == Decimal:
        return Decimal(val)
    if type_hint == date:
        return datetime.strptime(val, "%Y-%m-%d").date()
    if type_hint == datetime:
        # Handle timestamp with or without microseconds
        val = val.split("+")[0] # Remove timezone if present
        try:
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.fromisoformat(val)
    return val

def import_dump(dump_path):
    if not dump_path or not os.path.exists(dump_path):
        print(f"Error: Backup file not found at {dump_path}")
        return

    print(f"\nWARNING: This will OVERWRITE your current SQLite database at app/data/xpensetracker.db")
    print(f"Any changes made since the backup was created will be LOST.")
    confirm = input("Do you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        return

    print(f"\n--- Starting Migration ---")
    print(f"Source: {dump_path}")
    
    # 1. Setup SQLite
    sqlite_path = "app/data/xpensetracker.db"
    sqlite_url = f"sqlite:///./{sqlite_path}"
    
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    
    print(f"Target: {sqlite_path}")
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SqliteSession = sessionmaker(bind=sqlite_engine)
    
    # Create tables
    print("Initializing SQLite tables...")
    Base.metadata.drop_all(bind=sqlite_engine)
    Base.metadata.create_all(bind=sqlite_engine)
    
    session = SqliteSession()
    
    # 2. Parse SQL Dump
    try:
        with open(dump_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        in_copy_block = False
        count = 0
        
        print("Migrating records...")
        for line in lines:
            if line.startswith("COPY public.expenses"):
                in_copy_block = True
                continue
            
            if in_copy_block:
                if line.startswith(r"\."):
                    in_copy_block = False
                    continue
                
                parts = line.rstrip("\n").split("\t")
                # Dump Order: id, date, category, description, amount, currency, amount_eur, exchange_rate, receipt_image_path, is_verified, created_at, updated_at, type
                
                if len(parts) < 13:
                    continue
                
                exp = Expense(
                    id=parse_value(parts[0], int),
                    date=parse_value(parts[1], date),
                    category=parts[2],
                    description=parse_value(parts[3], str),
                    amount=parse_value(parts[4], Decimal),
                    currency=parse_value(parts[5], str),
                    amount_eur=parse_value(parts[6], Decimal),
                    exchange_rate=parse_value(parts[7], Decimal),
                    receipt_image_path=parse_value(parts[8], str),
                    is_verified=parse_value(parts[9], bool),
                    created_at=parse_value(parts[10], datetime),
                    updated_at=parse_value(parts[11], datetime),
                    type=parse_value(parts[12], str)
                )
                session.add(exp)
                count += 1
        
        session.commit()
        print(f"Success: Migrated {count} records.")
        print(f"--------------------------")
        print(f"Next step: Set DB_TYPE=sqlite in your .env and restart the app.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate PostgreSQL dump to SQLite")
    parser.add_argument("--file", help="Path to the .sql dump file. If omitted, the latest backup is used.")
    
    args = parser.parse_args()
    
    dump_file = args.file
    if not dump_file:
        dump_file = get_latest_backup()
        if dump_file:
            print(f"No file specified. Found latest backup: {dump_file}")
        else:
            print("Error: No backup files found in 'backups/' directory.")
            sys.exit(1)
            
    import_dump(dump_file)

