import asyncio
import logging
import signal
from bot_setup import configure_bot, create_bot
from db_setup import initialize_db_pool, shutdown_db_pool
from error_handler import setup_logging
from cogs.bank_cog import BankCog
from cogs.event_cog import setup as event_cog_setup


async def setup_cogs(bot, pool):
    """Load all cogs for the bot."""
    try:
        await event_cog_setup(bot, pool)
        await bot.add_cog(BankCog(bot, pool))
        logging.info("Cogs loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading cogs: {e}")
        raise


async def shutdown(bot, pool):
    """Gracefully shut down the bot and database pool."""
    logging.info("Shutting down bot and closing database connections...")
    if pool:
        await shutdown_db_pool(pool)
    await bot.close()
    logging.info("Shutdown complete.")


async def main():
    setup_logging()

    pool = await initialize_db_pool()
    bot = create_bot()
    DISCORD_TOKEN = configure_bot()

    try:
        # Load cogs
        await setup_cogs(bot, pool)

        # Start the bot
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logging.error(f"Error in main function: {e}")
    finally:
        await shutdown(bot, pool)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(shutdown(bot=None, pool=None)))

    loop.run_until_complete(main())
