import aiomysql
import asyncio
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.ERROR)
# Load environment variables
load_dotenv("db_configs.env")
DBHOST = os.getenv("DBHOST")
DBPORT = int(os.getenv("DBPORT"))
DBUSER = os.getenv("DBUSER")
DBPASSWORD = os.getenv("DBPASSWORD")
DBNAME = os.getenv("DBNAME")
if not all([DBHOST, DBPORT, DBUSER, DBPASSWORD, DBNAME]):
    raise ValueError("One or more database configuration environment variables are missing.")
pool = None


async def create_db_pool():
    global pool
    try:
        pool = await aiomysql.create_pool(
            host=DBHOST,
            port=DBPORT,
            user=DBUSER,
            password=DBPASSWORD,
            db=DBNAME,
            autocommit=True,  # Optional: set autocommit if you want automatic commits
            minsize=1,        # Minimum connections in the pool
            maxsize=10        # Maximum connections in the pool
        )
        if pool is not None:
            logging.info("Database pool created successfully.")
            logging.info(f"Database pool size: {pool.size()}")
    except aiomysql.Error as e:
        logging.error(f"Error creating database pool: {e}")
        pool = None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        pool = None
    return pool


async def close_db_pool():
    global pool
    if pool is not None:
        try:
            pool.close()
            await pool.wait_closed()
            logging.info("Database pool closed successfully.")
        except aiomysql.Error as e:
            logging.error(f"Error closing database pool: {e}")
        except Exception as e:
            logging.error(f"Unexpected error when closing the database pool: {e}")


# Example usage
async def main():
    await create_db_pool()
    # Perform your database operations here
    await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
