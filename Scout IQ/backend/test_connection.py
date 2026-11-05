
from sqlalchemy import text
from database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT COUNT(*) FROM players;")
        )

        count = result.scalar_one()

        print("Database connection successful!")
        print(f"Players in PostgreSQL: {count}")

except Exception as error:
    print("Database connection failed!")
    print(f"Error: {error}")
