# init_db.py
# Run this once to create the tables in Neon and verify the connection works.
#
# Usage (from backend/ directory, with your venv active):
#   python -m db.init_db

import asyncio
from db.database import init_db, engine


async def main():
    print("Connecting to Neon and creating tables (if they don't already exist)...")
    await init_db()
    print("Done. Tables created: users, documents, conversations, messages")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())