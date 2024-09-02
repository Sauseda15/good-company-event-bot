from utils.db import create_db_pool, close_db_pool


async def initialize_db_pool():
    pool = await create_db_pool()
    return pool


async def shutdown_db_pool(pool):
    await close_db_pool(pool)
