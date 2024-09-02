from decimal import Decimal
import traceback
import discord
from typing import Dict
import datetime
import logging
from dotenv import load_dotenv
import os
from utils.bank_util import openbank, savebank
from utils.event_util import event_token_add

logging.basicConfig(level=logging.INFO)
# Create a logger
logger = logging.getLogger(__name__)
# Set the logging level to INFO
logger.setLevel(logging.INFO)
# Create a console handler
console_handler = logging.StreamHandler()
# Add the console handler to the logger
logger.addHandler(console_handler)
token_types = ["Event Token", "Leadership Token", "Competitive Token", "War Token"]

global DISCORD_TOKEN, EVENT_CHANNEL, VODS_CHANNEL
load_dotenv(os.path.join(os.getcwd(), "config", "event_configs.env"))
EVENT_CHANNEL = int(os.getenv("EVENT_CHANNEL"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VODS_CHANNEL = int(os.getenv("VODS_CHANNEL"))

photos_folder = os.path.join(os.getcwd(), "photos")

company_lead_roles = {
    "STR Bruiser Lead": 1168251564419461120,
    "INT Bruiser Lead": 1168251540046364836,
    "Healer Lead": 1168251525043339294,
    "Utility Mage": 1168251553405223022,
    "Assassin Team Lead": 1167943700983316591,
}
company_roles = {
    "settler": 1040383506481692693,
    "officer": 1040383501188468886,
    "consul": 1040383486856540181,
    "governor": 1040383340320149554
}

payout_event_tokens = ["War Token", "Leadership Token", "Competitive Token"]


class Event:
    """
    Class to handle a Discord Event's Lifecycle.

    Attributes:
    is_ongoing (bool): Whether the event is ongoing.
    channel (discord.TextChannel): The channel where the event is taking place.
    bot (commands.Bot): The bot instance.
    event_start_time (datetime.datetime): The time when the event started.
    event_end_time (datetime.datetime): The time when the event ended.
    participants (Dict[int, EventParticipant]): The participants in the event.
    joined_times (Dict[int, datetime.datetime]): The times when participants joined the event.
    leave_times (Dict[int, datetime.datetime]): The times when participants left the event.
    rejoined_times (Dict[int, datetime.datetime]): The times when participants rejoined the event.
    pool: The connection pool to the database.

    Methods:
    reset: Resets the event attributes.
    initialize: Initializes the event with the given channel.
    send_token_embed: Sends a token embed to the given member.
    create_event_file: Creates an event file with the given event data.
    handle_vod_review: Handles the VOD review for the given member.
    finalize: Finalizes the event and calculates the time spent by each member and updates the bank, and sends the token to each member.
    """
    def __init__(self, bot, pool):
        self.is_ongoing = False
        self.channel = None
        self.bot = bot
        self.event_start_time = None
        self.event_end_time = None
        self.participants: Dict[int, EventParticipant] = {}
        self.joined_times = {}
        self.leave_times = {}
        self.rejoined_times = {}
        self.pool = pool

    async def reset(self):
        self.is_ongoing = False
        self.channel = None
        self.participants.clear()
        self.joined_times.clear()
        self.leave_times.clear()
        self.rejoined_times.clear()

    async def initialize(self, after):
        logger.info("Event Has Started!")
        self.is_ongoing = True
        self.channel = after.channel
        self.event_start_time = datetime.datetime.utcnow()
        for member in self.channel.members:
            self.participants[member.id] = EventParticipant(member.id)
            self.participants[member.id].current_start_time = self.event_start_time

    async def send_token_embed(self, member, token, event_name, bank):
        member_id = member.id
        member_discord = self.channel.guild.get_member(member_id)
        company = next((role_name for role_name, role_id in company_roles.items() if discord.utils.get(member_discord.roles, id=role_id)), None)
        file = discord.File(os.path.join(photos_folder, f"{token}.png"), filename="token.png")
        embed = discord.Embed(
            title=f"**You just received a {token}!**",
            description=f"Congrats! You just received a {token} for taking part in {event_name}",
            color=discord.Color.green(),
        ).add_field(name=f"Current {token} balance:", value=str(bank[company][member_id][token]))
        embed.set_image(url="attachment://token.png")
        try:
            await member.send(file=file, embed=embed)
        except discord.Forbidden:
            logger.warning(f"Cannot send message to {member.display_name} due to privacy settings.")

    async def create_event_file(self, event_data):
        folder_path = "event_files"
        os.makedirs(folder_path, exist_ok=True)
        for event_name, event_info in event_data.items():
            filename = os.path.join(folder_path, f"{event_name}_event.txt")
            try:
                with open(filename, "w") as file:
                    # Write event general information
                    file.write(
                        f"Event Name: {event_name}\n"
                        f"Event Duration: {event_info['event_duration']} seconds\n\n"
                    )
                    for member_id, member_data in event_info["members"].items():
                        # Write member-specific information
                        member_nick = self.channel.guild.get_member(int(member_id)).display_name
                        file.write(
                            f"Member ID: {member_id}\n"
                            f"Member Nickname: {member_nick}\n"
                            f"Token Earned: {member_data['Token Earned']}\n"
                            f"Start Balance: {member_data['start_balance']}\n"
                            f"End Balance: {member_data['end_balance']}\n"
                            f"Time Spent in Event: {member_data['duration']} seconds\n\n"
                        )
                logging.info(f"Event file '{filename}' created successfully.")
            except IOError as io_err:
                logging.error(f"IOError when creating event file '{filename}': {io_err}")
            except Exception as e:
                logging.error(f"Error when creating event file '{filename}': {e}")

    async def handle_vod_review(self, member_discord, token, event_name):
        if token == "War Token":
            file = discord.File(os.path.join(photos_folder, f"{token}.png"), filename=f"token.png")
            embed = discord.Embed(
                title="**You just received a Pending Token!**",
                description=f"You just received a pending {token} for taking part in {event_name}, you must post a VOD review to receive the token!",
                color=discord.Color.green(),
            )
            embed.set_image(url=f"attachment://token.png")
            try: 
                await member_discord.send(file=file, embed=embed)
            except discord.Forbidden:
                logger.warning(f"Cannot send message to {member_discord.display_name} due to privacy settings.")

    async def finalize(self, before):
        # Finalize the event and calculate the time spent by each member and update the bank send the token to each member 
        logger.info("Event Has Ended")
        self.is_ongoing = False
        description = before.description
        if self.channel is None:
            self.channel = before.channel
        token = None 
        for token_type in token_types:
            if token_type in description:
                token = token_type
                logging.info(f"Token type found: {token_type}")
                break
        if token is None:
            token = "Event Token" # Default to Event Token if no token type is found
        self.event_end_time = datetime.datetime.utcnow()
        bank = await openbank(self.pool)
        event_duration = (self.event_end_time - self.event_start_time).total_seconds()
        event_name = before.name
        event_data = {event_name: {"event_duration": event_duration, "members": {}}}

        try:
            for member in self.participants.values():
                member_id = member.user_id
                member_discord = self.channel.guild.get_member(member_id)
                if not member_discord:
                    continue
                member.event_ends()
                members_needing_vod_review = []
                needs_vod_review = True   # Set to True if the member needs a VOD review
                precise_duration = member.get_total_time_spent()
                company = next((role_name for role_name, role_id in company_roles.items() if discord.utils.get(member_discord.roles, id=role_id)), None)
                for role_name, role_id in company_lead_roles.items():
                    if discord.utils.get(member_discord.roles, id=role_id):
                        needs_vod_review = False
                        break
                if needs_vod_review and token == "War Token":
                    members_needing_vod_review.append(member_discord.display_name) # Add the member to the list of members needing a VOD review
                    await self.handle_vod_review(member_discord, token, event_name)
                    continue  # Skip the rest of the code and go to the next member
                if company:
                    bank.setdefault(company, {}) # Create the company key if it doesn't exist
                    member_id = str(member_id) # Convert to string to use as key in bank
                    # Check if the company key exists in the bank dictionary
                    start_balance, end_balance, bank = await event_token_add( member_id, company, bank, token)
                    member_data = {
                        "start_balance": start_balance,
                        "join_time": self.joined_times.get(member_id, self.event_start_time),
                        "Token Earned": token,
                        "end_balance": end_balance,
                        "duration": precise_duration,
                    }
                    event_data[event_name]["members"][member_id] = member_data
                    await self.send_token_embed(member_discord, token, before.name, bank)
        except Exception as e:
            traceback.print_exc() # Print the traceback to the console
            logging.error(f"Error in finalize: {e}")
        # Send vod reviews needed to VOD Channel
        if token == "War Token":
            await self.bot.get_channel(VODS_CHANNEL).send(f"**{token} VOD Reviews Needed:**\n{', '.join(members_needing_vod_review)}")
        await savebank(bank, self.pool)
        await self.create_event_file(event_data)
        await self.reset()


class EventParticipant:
    """
    Class to handle a participant in an event.

    Attributes:
    user_id (int): The user ID of the participant.
    time_in_event (datetime.timedelta): The time spent by the participant in the event.
    current_start_time (datetime.datetime): The start time of the current period.

    Methods:
    join_event: Update the current_start_time to the current time.
    leave_event: Calculate the duration of the current period and update time_in_event.
    event_ends: Calculate the time spent until now and update time_in_event.
    get_total_time_spent: Get the total time spent by the participant
    """
    def __init__(self, user_id):
        self.user_id = user_id
        self.time_in_event = datetime.timedelta(seconds=0) 
        self.current_start_time = None  # Store the start time of the current period

    def join_event(self):
        self.current_start_time = datetime.datetime.utcnow()

    def leave_event(self):
        if self.current_start_time:
            end_time = datetime.datetime.utcnow()
            duration = (end_time - self.current_start_time).total_seconds()
            duration = datetime.timedelta(seconds=duration)
            self.time_in_event += duration
            self.current_start_time = None

    def event_ends(self):
        # If the event ends, calculate time spent until now and update time_in_event
        if self.current_start_time:
            end_time = datetime.datetime.utcnow()
            duration = (end_time - self.current_start_time).total_seconds()
            duration = datetime.timedelta(seconds=duration)
            self.time_in_event += duration
            self.current_start_time = None

    def get_total_time_spent(self):
        return self.time_in_event


class GuildMemberEventParticipant:
    def __init__(self, member_id: int, tokens: int = 0) -> None:
        self.tokens = Decimal(tokens)
        self.war_tokens = Decimal(0)
        self.leadership_tokens = Decimal(0)
        self.competitive_tokens = Decimal(0)
        self.member_id = str(member_id)  # Store as string if it's used as a string
        self.war_payout: Decimal = Decimal(0)
        self.leadership_payout: Decimal = Decimal(0)
        self.competitive_payout: Decimal = Decimal(0)

    def war_token_payout(self, gold_per_wartoken: Decimal) -> Decimal:
        war_token_payout = self.war_tokens * gold_per_wartoken
        self.war_payout += war_token_payout
        return war_token_payout

    def leadership_token_payout(self, gold_per_leadershiptoken: Decimal) -> Decimal:
        leadership_token_payout = self.leadership_tokens * gold_per_leadershiptoken
        self.leadership_payout += leadership_token_payout
        return leadership_token_payout

    def competitive_token_payout(self, gold_per_competitivetoken: Decimal) -> Decimal:
        competitive_token_payout = self.competitive_tokens * gold_per_competitivetoken
        self.competitive_payout += competitive_token_payout
        return competitive_token_payout

    def weekly_payout(self) -> Decimal:
        return self.war_payout + self.leadership_payout + self.competitive_payout

    def reset_tokens(self) -> None:
        """Reset the member's tokens to zero."""
        self.tokens = Decimal(0)

    def update_tokens_from_bank(self, bank, role_name) -> None:
        member_bank_info = bank.get(role_name, {}).get(self.member_id, {})
        self.war_tokens += Decimal(member_bank_info.get("War Token", 0))
        self.leadership_tokens += Decimal(member_bank_info.get("Leadership Token", 0))
        self.competitive_tokens += Decimal(member_bank_info.get("Competitive Token", 0))
        self.tokens = self.war_tokens + self.leadership_tokens + self.competitive_tokens
