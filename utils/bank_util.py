import logging
import json
import discord
import asyncio
from functools import wraps

bank_lock = asyncio.Lock()
emoji_cache = {}

async def switch_token_emoji(bot, tokentype):
    if tokentype in emoji_cache:
        return emoji_cache[tokentype]

    emoji_name_map = {
        "Event Token": "event_token",
        "Leadership Token": "leadership_token",
        "Competitive Token": "competitive_token",
        "War Token": "war_token"
    }

    emoji_name = emoji_name_map.get(tokentype)
    if emoji_name:
        emoji = discord.utils.get(bot.emojis, name=emoji_name)
        if emoji:
            emoji_cache[tokentype] = str(emoji)
            return emoji_cache[tokentype]

    logging.warning(f"No matching emoji found for token type: {tokentype}")
    emoji_cache[tokentype] = "❓"  # Use a default or empty emoji string
    return emoji_cache[tokentype]

async def openbank(pool):
    logging.info(f"Acquiring connection from pool: {pool}")
    async with bank_lock:
        if pool is None:
            logging.error("Connection pool has not been initialized.")
            raise ValueError("Connection pool has not been initialized.")
        
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        logging.info("Creating the table if it doesn't exist...")
                        create_table_query = """
                        CREATE TABLE IF NOT EXISTS bank_data (
                            `key` VARCHAR(255) PRIMARY KEY,
                            `data` JSON NOT NULL
                        )
                        """
                        await cur.execute(create_table_query)
                        
                        logging.info("Fetching bank data...")
                        await cur.execute("SELECT `data` FROM `bank_data` WHERE `key` = 'bank'")
                        result = await cur.fetchone()
                        if result is not None:
                            return json.loads(result[0])
                        else:
                            logging.info("No result found, returning empty dictionary.")
                            return {}
                    except Exception as e:
                        logging.error(f"Error in openbank function: {e}")
                        return {}
        except Exception as e:
            logging.error(f"Error acquiring connection: {e}")
            raise

async def savebank(data, pool):
    async with bank_lock:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        await cur.execute("SELECT `data` FROM `bank_data` WHERE `key` = 'bank'")
                        result = await cur.fetchone()              
                        if result is not None:
                            existing_data = json.loads(result[0])
                            for role, users in data.items():
                                if role not in existing_data:
                                    existing_data[role] = {}
                                for user_id, tokens in users.items():
                                    existing_data[role].setdefault(user_id, {})
                                    for token_type, balance in tokens.items():
                                        existing_data[role][user_id][token_type] = balance
                        else:
                            existing_data = data           
                        serialized_data = json.dumps(existing_data)     
                        if result is not None:
                            await cur.execute("UPDATE `bank_data` SET `data` = %s WHERE `key` = 'bank'", (serialized_data,))
                        else:
                            await cur.execute("INSERT INTO `bank_data`(`key`, `data`) VALUES ('bank', %s)", (serialized_data,))         
                        await conn.commit()
                    except Exception as e:
                        logging.error(f"Error in savebank function: {e}")
                        await conn.rollback()
                        raise
        except Exception as e:
            logging.error(f"Error acquiring connection in savebank: {e}")
            raise

async def resetbank(pool):
    async with bank_lock:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        await cur.execute("DELETE FROM `bank_data` WHERE `key` = 'bank'")
                        await conn.commit()
                    except Exception as e:
                        logging.error(f"Error in resetbank function: {e}")
                        await conn.rollback()
                        raise
        except Exception as e:
            logging.error(f"Error acquiring connection in resetbank: {e}")
            raise
