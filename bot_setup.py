import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configure_bot(env_path: str = "event_configs.env") -> str:
    load_dotenv(env_path)
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        logger.error("Discord token not found. Please check your .env file.")
        raise ValueError("Discord token not found. Please check your .env file.")
    logger.info("Discord token loaded successfully.")
    return DISCORD_TOKEN

def create_bot() -> commands.Bot:
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="/", intents=intents)
    logger.info("Bot created successfully.")
    return bot