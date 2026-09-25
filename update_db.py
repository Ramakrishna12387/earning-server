from app import app, db
from sqlalchemy import text

with app.app_context():
    connection = db.engine.connect()

    connection.execute(
        text("ALTER TABLE player ADD COLUMN wins INTEGER DEFAULT 0")
    )

    connection.execute(
        text("ALTER TABLE player ADD COLUMN losses INTEGER DEFAULT 0")
    )

    connection.execute(
        text("ALTER TABLE player ADD COLUMN games_played INTEGER DEFAULT 0")
    )

    connection.commit()
    connection.close()

    print("DATABASE UPDATED")