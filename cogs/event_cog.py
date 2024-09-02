import logging
import discord
from discord.ext import commands  
from utils.db import openbank, savebank
import asyncio
from views.views import EventParticipant, Event


class EventCog(commands.Cog):
    """
    EventCog is a cog that listens to various events in the discord server.
    
        Attributes:
        bot (commands.Bot): The discord bot instance.
        pool (asyncpg.pool.Pool): The connection pool to the database.
        leave_channel (int): The channel id where the bot sends a message when a member leaves the server.
        company_roles (dict): A dictionary containing the company roles and their respective role ids.
        ally_roles (dict): A dictionary containing the ally roles and their respective role ids.
        current_event (Event): The current event instance.
        """
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool
        self.leave_channel = 1162190524619444264
        self.company_roles = {
            "settler": 1040383506481692693,
            "officer": 1040383501188468886,
            "consul": 1040383486856540181,
            "governor": 1040383340320149554
        }
        self.ally_roles = {
            "Ally": 1052890530910044181,
            "Selected for War": 1047718256498192405
        }
        self.current_event = None

    @commands.Cog.listener()
    async def on_ready(self): # Called when the bot is ready
        logging.info(f"Logged in as {self.bot.user.name}")
        guild_id = 1040334471028801639
        guild = self.bot.get_guild(guild_id)
        if guild: # Check if the bot is in the guild
            logging.info(f"Connected to guild: {guild.name}")
        # Syncing application commands
        try:
            synced = await self.bot.tree.sync() # Sync the application commands
            logging.info(f"Successfully synced {len(synced)} application commands")
        except discord.HTTPException as e: # Handle HTTP errors
            logging.error(f"HTTP error occurred while syncing application commands: {e}")
        except Exception as e: # Handle other errors
            logging.error(f"An unexpected error occurred while syncing application commands: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            bank = await openbank(self.pool)
        except Exception as e:
            logging.error(f"Error opening bank for member {member.id}: {e}")
            return

        try: # Remove the member from the bank
            member_id = str(member.id)
            for role_name in bank:
                if member_id in bank[role_name]:
                    del bank[role_name][member_id]
                    logging.info(f"Removed {member.name} from bank")
            await savebank(bank, self.pool)
        except Exception as e:
            logging.error(f"Error updating bank for member {member.id}: {e}")
 
        try: # Send a message to the leave channel
            channel = self.bot.get_channel(self.leave_channel)
            await channel.send(embed=discord.Embed(
                title=f"{member.display_name} has left the server!",
                description=f"Member was in the following roles: {', '.join(map(str, member.roles))}",
                color=discord.Color.red()
            ))
        except discord.HTTPException as e:
            logging.error(f"Failed to send leave message for member {member.id}: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if self.current_event and self.current_event.is_ongoing and self.current_event.channel:
            if self.current_event.channel == after.channel and before.channel != after.channel:
                logging.info(f"{member.display_name} joined the event channel")
                event_participant = self.current_event.participatns.get(member.id)
                if event_participant:
                    event_participant.join_event()
                else:
                    logging.info(f"{member.display_name} is not part of the event")
                    event_participant = EventParticipant(member.id)
                    self.current_event.participants[member.id] = event_participant
                    event_participant.join_event()
            elif self.current_event.channel == before.channel and before.channel != after.channel:
                logging.info(f"{member.display_name} left the event channel")
                event_participant = self.current_event.participants.get(member.id)
                event_participant.leave_event()

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        try:
            if before.status != after.status:
                if str(after.status) == "EventStatus.active":
                    self.current_event = Event(self.bot, self.pool)
                    await self.current_event.initialize(before)
                elif str(after.status) == "EventStatus.completed":
                    await self.current_event.finalize(before)
                else:
                    logging.error(f"Unhandled event status: {after.status}")
        except Exception as e:
            logging.error(f"Error handling scheduled event update: {e}")
        finally:
            # Cleanup or logging that should occur regardless of the exception
            logging.info(f"Event update completed: {after.name}")


def setup(bot, pool):
    bot.add_cog(EventCog(bot, pool))
