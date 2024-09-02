import datetime
import os
import aiomysql
from decimal import Decimal
import discord
from discord.ext import commands
from typing import Union
from utils.bank_util import openbank, savebank, switch_token_emoji
from views.views import GuildMemberEventParticipant
import logging

logging.basicConfig(level=logging.INFO)
photos_folder = os.path.join(os.getcwd(), "photos")
company_roles = {
    "settler": 1040383506481692693,
    "officer": 1040383501188468886,
    "consul": 1040383486856540181,
    "governor": 1040383340320149554
}
token_types = [

    "Event Token",
    "Leadership Token",
    "Competitive Token",
    "War Token"
    ]
payout_event_tokens = [
    "War Token", 
    "Leadership Token", 
    "Competitive Token"
    ]

async def paginate_pm_messages(member, messages, max_messages_per_page=5):
    pages = [messages[i:i + max_messages_per_page] for i in range(0, len(messages), max_messages_per_page)]
    for i, page in enumerate(pages):
        embed = discord.Embed(
            title=f"Payout Information for {member.display_name} (Page {i+1}/{len(pages)})",
            color=discord.Color.green()
        )
        for message in page:
            embed.add_field(
                name=message["name"],
                value=message["value"],
                inline=False
            )
        try:
            await member.send(embed=embed)
        except discord.errors.Forbidden:
            logging.error(f"Failed to send page {i+1} to {member.display_name} due to privacy settings.")
            return False  # Pagination halted due to a sending error
    print(f"Pagination completed successfully")
    return True  # Pagination completed successfully

def create_payout_file(pm_sent, payouts, breakdown, construct_date):
    folder_path = os.path.join(os.getcwd(), "weekly_payouts")
    filename = os.path.join(folder_path, f"monday_payout_{construct_date}.txt")
    try:
        # Create the directory if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        with open(filename, "w") as file:
            # Write member payouts
            file.write("Member: Payout gold\n")
            for member, payout in payouts.items():
                # Check if payout is a Decimal and handle it accordingly
                if isinstance(payout, Decimal):
                    file.write(f"{member}: {payout:.2f} gold\n")
                else:
                    logging.error(f"Unexpected payout type: {type(payout)} for member {member}")
            
            # Write PM Sent status
            file.write(f"\nPm Sent: {pm_sent}\n")

            # Write token type breakdown
            file.write("\nBreakdown\n")
            for token_type, payout_value in breakdown.items():
                if isinstance(payout_value, Decimal):
                    file.write(f"{token_type}: {payout_value:.2f} gold\n")
                else:
                    logging.error(f"Unexpected breakdown value type: {type(payout_value)} for token type {token_type}")
        logging.info(f"Payout file '{filename}' created successfully.")
    except IOError as io_err:
        logging.error(f"IOError when creating payout file '{filename}': {io_err}")  
    except Exception as e:
        logging.error(f"General error when creating payout file '{filename}': {e}")


class BankCog(commands.Cog):
    """"
    A cog that handles the bank system for the Good Company Discord server.

    Commands:
    - /addtokens*: Adds tokens to a user's balance.
    - /removetokens*: Removes tokens from a user's balance.
    - /balance [@user]*: Shows a user's current balance.
    - /ledger*: Lists all member's balances.
    - /payout*: Pays out gold income to all members of a role based on tokens.

    * Requires administrator permissions to use.
    """
    def __init__(self, bot: commands.Bot, pool) -> None:
        self.bot: commands.Bot = bot
        self.pool = pool

    @commands.hybrid_command(name="payout", description="Allows you to pay out gold income to all members of a role based on tokens.")
    async def payout(self, ctx: commands.Context, income: float, dry_run: bool = False) -> None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("You do not have permission to use this command.")
            return
        
        guild_members_participated = {}
        bank = await openbank(self.pool)  # Bank data
        weekly_company_income = Decimal(str(income))  # Income for the week
        weekly_company_payout = Decimal('0.6') * weekly_company_income  # Total payout for the week
        war_token_ratio = Decimal('3.0')
        leadership_token_ratio = Decimal('2.0')
        competitive_token_ratio = Decimal('1.0')
        weekly_company_payout_ratio = weekly_company_payout / (war_token_ratio + leadership_token_ratio + competitive_token_ratio)  
        weekly_wartoken_payout = war_token_ratio * weekly_company_payout_ratio  # 76.36% for war tokens
        weekly_leadershiptoken_payout = leadership_token_ratio * weekly_company_payout_ratio  # 10.92% for leadership tokens
        weekly_competitivetoken_payout = competitive_token_ratio * weekly_company_payout_ratio  # 12.72% for competitive tokens
        total_wartokens_earned = Decimal('0.0')
        total_leadershiptokens_earned = Decimal('0.0')
        total_competitivetokens_earned = Decimal('0.0')
        war_emoji = await switch_token_emoji(self.bot, "War Token")
        leadership_emoji = await switch_token_emoji(self.bot, "Leadership Token")
        competitive_emoji = await switch_token_emoji(self.bot, "Competitive Token")

        for role_name, role_id in company_roles.items():
            for member in ctx.guild.members:
                if role_id in [role.id for role in member.roles]:
                    guild_member = GuildMemberEventParticipant(member.id)
                    guild_member.update_tokens_from_bank(bank, role_name)
                    guild_members_participated[str(member.id)] = guild_member
                    total_wartokens_earned += Decimal(guild_member.war_tokens)
                    total_leadershiptokens_earned += Decimal(guild_member.leadership_tokens)
                    total_competitivetokens_earned += Decimal(guild_member.competitive_tokens)
                    for tokentype in payout_event_tokens:
                        bank[role_name].setdefault(str(member.id), {})  # Ensure the member_id key exists
                        if tokentype in bank[role_name][str(member.id)]:
                            bank[role_name][str(member.id)][tokentype] = 0  # Reset the tokens for the next week

        total_tokens_earned = (
            total_wartokens_earned + total_leadershiptokens_earned + total_competitivetokens_earned
        )
        if total_tokens_earned == 0:
            await ctx.send("No tokens have been earned this week. No payout necessary.")
            return

        gold_per_wartoken = weekly_wartoken_payout / total_wartokens_earned  # Gold per war token
        gold_per_leadershiptoken = weekly_leadershiptoken_payout / total_leadershiptokens_earned  # Gold per leadership token
        gold_per_competitivetoken = weekly_competitivetoken_payout / total_competitivetokens_earned  # Gold per competitive token

        monday = datetime.datetime.today() - datetime.timedelta(days=datetime.datetime.today().weekday())
        construct_date = monday.strftime("%m/%d/%Y")

        # Prepare payouts and breakdown
        payouts = {}
        payout_breakdown = {
            "War Token Payout": Decimal('0.00'),
            "Leadership Token Payout": Decimal('0.00'),
            "Competitive Token Payout": Decimal('0.00')
        }
        payout_pm_sent = True
        for member_id, guild_member in guild_members_participated.items():
            discord_member = await ctx.guild.get_member(int(member_id))  # Get the Discord member object
            if discord_member:
                war_token_payout = guild_member.war_token_payout(gold_per_wartoken)  # Get the war token payout for the member
                leadership_token_payout = guild_member.leadership_token_payout(gold_per_leadershiptoken)
                competitive_token_payout = guild_member.competitive_token_payout(gold_per_competitivetoken)
                total_payout = war_token_payout + leadership_token_payout + competitive_token_payout
                payouts[discord_member.display_name] = total_payout
                # Update the breakdown
                payout_breakdown["War Token Payout"] += war_token_payout
                payout_breakdown["Leadership Token Payout"] += leadership_token_payout
                payout_breakdown["Competitive Token Payout"] += competitive_token_payout
                messages = [
                    {"name": f"{war_emoji} War Tokens", "value": f"{war_token_payout:.2f} gold"},
                    {"name": f"{leadership_emoji} Leadership Tokens", "value": f"{leadership_token_payout:.2f} gold"},
                    {"name": f"{competitive_emoji} Competitive Tokens", "value": f"{competitive_token_payout:.2f} gold"},
                    {"name": "Overall Total", "value": f"{total_payout:.2f} gold"}
                ]
                if not dry_run:
                    if not await paginate_pm_messages(discord_member, messages):
                        payout_pm_sent = False
                if dry_run and discord_member.id == 342142929533403136:
                    if not await paginate_pm_messages(discord_member, messages):
                        payout_pm_sent = False

        # Sort payouts alphabetically by member name
        sorted_payouts = dict(sorted(payouts.items()))

        if not dry_run:
            await savebank(bank, self.pool)  # Only save if not a dry run

        # Create an overall payout file
        create_payout_file(payout_pm_sent, sorted_payouts, payout_breakdown, construct_date)

    @commands.hybrid_command(name="balance", description="Show's your current Event Balance.")
    async def balance(self, ctx: commands.Context, target: Union[discord.Member, discord.Role] = None) -> None:
        try:
            if target is None:
                target = ctx.author
            bank = await openbank(self.pool)

            if isinstance(target, discord.Member):
                if target != ctx.author and not (ctx.author.guild_permissions and ctx.author.guild_permissions.manage_events):
                    await ctx.send("You don't have the required permissions to view other members' balances.", ephemeral=True)
                    return
                member_id = str(target.id)
                total_balances = {}
                for role_name in company_roles:
                    role_data = bank.get(role_name, {})
                    member_data = role_data.get(member_id, {})
                    for tokentype in token_types:
                        total_balances[tokentype] = total_balances.get(tokentype, 0) + member_data.get(tokentype, 0)
                # Check if all balances are 0
                if all(balance == 0 for balance in total_balances.values()):
                    await ctx.send("You don't have any tokens in the bank.", ephemeral=True)
                    return
                # Create an embed to display the balances
                embed = discord.Embed(title=f"{target.display_name if target.display_name else target.name}'s current balances", color=discord.Color.blue())
                for tokentype, balance in total_balances.items():
                    token_emoji = await switch_token_emoji(self.bot, tokentype)  # Get the emoji for the token type
                    embed.add_field(name=f"{token_emoji} {tokentype} Balance:", value=f"{balance} Token(s)")
                await ctx.send(embed=embed, ephemeral=True)
            elif isinstance(target, discord.Role) and target.name.lower() in [role.lower() for role in company_roles]:
                total_balances_for_role = {tokentype: 0 for tokentype in token_types}
                for member in ctx.guild.members:
                    if target in member.roles:
                        member_id = str(member.id)
                        role_data = bank.get(target.name.lower(), {})
                        member_data = role_data.get(member_id, {})
                        for tokentype in token_types:
                            total_balances_for_role[tokentype] += member_data.get(tokentype, 0)
                if all(balance == 0 for balance in total_balances_for_role.values()):
                    await ctx.send(f"No members have any tokens in the bank for the {target.name} role.", ephemeral=True)
                    return
                embed = discord.Embed(title=f"Total balances for {target.name} role", color=discord.Color.blue())
                for tokentype, balance in total_balances_for_role.items():
                    embed.add_field(name=f"{tokentype} Balance:", value=f"{balance} Token(s)")
                await ctx.send(embed=embed, ephemeral=True)
            elif isinstance(target, discord.Role):
                await ctx.send("That is not a valid role.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in balance command: {e}")
            await ctx.send("An error occurred while processing your request.", ephemeral=True)


    @commands.hybrid_command(name="removetokens", description="Allows you to remove tokens from a player's Token Balance.")
    async def removetokens(self, ctx: commands.Context, user: discord.Member, tokentype: str, tokens: int) -> None:
        try:
            if ctx.author.guild_permissions.administrator:
                bank = await openbank(self.pool)
                company_role = None
                for token in token_types:
                    if tokentype.lower().strip() == token.lower().strip():
                        tokentype = token
                        break
                    else:
                        await ctx.send(f"{tokentype} is not a recognized token type. use one of the following: {', '.join(token_types)}", ephemeral=True)
                        return
                for role_name, role_id in company_roles.items():
                    role = discord.utils.get(user.roles, id=role_id)
                    if role:
                        company_role = role_name
                        break
                if company_role is None:
                    await ctx.send("The user doesn't have a recognized company role.", ephemeral=True)
                    return
                user_id = str(user.id)
                if company_role not in bank or user_id not in bank[company_role]:
                    await ctx.send(f"{user.display_name if user.display_name else user.name} does not have a balance in the bank for {company_role}.", ephemeral=True)
                    return
                if tokens >= 0:
                    if tokentype in bank[company_role][user_id]:
                        # Ensure the balance doesn't go below 0
                        bank[company_role][user_id][tokentype] = max(0, bank[company_role][user_id][tokentype] - tokens)
                    else:
                        await ctx.send(f"{user.display_name} does not have any {tokentype} to remove", ephemeral=True)
                        return
                else:
                    await ctx.send("You can't remove a negative amount of tokens.", ephemeral=True)
                    return
                await savebank(bank, self.pool)
                await ctx.send(embed=discord.Embed(
                    title=f"Removed {tokens} token(s) from {user.display_name if user.display_name else user.name}'s {tokentype} Balance.",
                    description=f"New {tokentype} balance: {bank[company_role][user_id][tokentype]}",
                    color=discord.Color.blue()
                ), ephemeral=True)
            else:
                await ctx.send("You don't have permissions to remove tokens.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in removetokens command: {e}")
            await ctx.send("An error occurred while processing your request.", ephemeral=True)

    @commands.hybrid_command(name="addtokens", description="Allows you to add tokens to a player's Token Balance.")
    async def addtokens(self, ctx: commands.Context, user: discord.Member, tokentype: str, tokens: int) -> None:
        logging.info("Add tokens command started")
        if ctx.author.guild_permissions.administrator:
            try:
                for token in token_types:
                    if tokentype.lower().strip() == token.lower().strip(): 
                        tokentype = token
                        break
                bank = await openbank(self.pool)
                company_role = None
                for role_name, role_id in company_roles.items():
                    role = discord.utils.get(user.roles, id=role_id)
                    if role:
                        company_role = role_name
                        break
                if company_role is None:
                    await ctx.send("The user doesn't have a recognized company role.", ephemeral=True)
                    return
                member_id = str(user.id)
                bank.setdefault(company_role, {}).setdefault(member_id, {}).setdefault(tokentype, 0)
                bank[company_role][member_id][tokentype] += tokens # Add the tokens to the user's balance
                await savebank(bank, self.pool)
                await ctx.send(embed=discord.Embed(
                title=f"Added {tokens} {tokentype}(s) to {user.display_name if user.display_name else user.name}'s {company_role} balance.",
                description=f"New balance: {bank[company_role][member_id][tokentype]} {tokentype}(s)",
                color=discord.Color.blue()), ephemeral=True)
                file = discord.File(os.path.join(photos_folder, f"{tokentype}.png"), filename=f"token.png")  # Create a file object              
                embed = discord.Embed(title=f"Added {tokens} token(s) to your {company_role} {tokentype} Token Balance.", description=f"New balance: {bank[company_role][member_id][tokentype]} Token(s)", color=discord.Color.blue())
                embed.set_image(url=f"attachment://token.png")
                await user.send(file=file, embed=embed)
            except Exception as e:
                logging.error(f"Error in addTokens: {e}")
                await ctx.send("An error occurred while processing your request.", ephemeral=True)
        else:
            await ctx.send("You don't have permissions to add Tokens.", ephemeral=True)

    @commands.hybrid_command(name="ledger", description="Lists all member's balances")
    async def ledger(self, ctx: commands.Context, tokentype: str) -> None:
        message = await ctx.defer(ephemeral=True)
        if ctx.author.guild_permissions.manage_events:
            # Validate the token type
            for token in token_types:
                if tokentype.lower().strip() == token.lower().strip():
                    tokentype = token
                    break
            else:
                await ctx.send(f"{tokentype} is not a recognized token type. Use one of the following: {', '.join(token_types)}", ephemeral=True)
                return

            bank = await openbank(self.pool)
            emb = discord.Embed(title="Good Company Ledger", color=discord.Color.blue())
            no_tokens_found = True  # Assume no tokens are found initially

            for role_name, role_id in company_roles.items():
                role = discord.utils.get(ctx.guild.roles, id=role_id)
                if role:
                    header = f"**{role_name.capitalize()} Balances**"
                    names = []

                    for member_id, tokens in bank.get(role_name, {}).items():
                        try:
                            member = await ctx.guild.fetch_member(int(member_id))
                            balance = tokens.get(tokentype, 0)  # Get the balance for the specified token type
                            if balance > 0:
                                no_tokens_found = False  # Tokens found, so set flag to False
                                nickname = member.display_name if member.display_name else member.name
                                names.append(f"{nickname}'s {tokentype}: {balance}")
                        except discord.NotFound:
                            pass

                    if names:
                        names_str = "\n".join(names)
                        emb.add_field(name=header, value=names_str)

            # Check if no tokens were found for any role
            if no_tokens_found:
                emb.description = f"No members have any tokens in the bank for the {tokentype} type."

            await ctx.send(embed=emb)
        else:
            await ctx.send("You don't have permissions to view the ledger.", ephemeral=True)



async def setup(bot: commands.bot, pool: aiomysql.Pool) -> None:
    try:
        await bot.add_cog(BankCog(bot, pool))
    except Exception as e:
        logging.error(f"Error loading bankcjson: {e}")