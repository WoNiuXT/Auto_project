from app.storage.db import DB

def get_db():
    db = None
    try:
        db = DB(port=5434)
        db.connect()
        db.init_tables()
    except Exception as e:
        print(f"[WARN] DB connection failed: {e}")
    return db
