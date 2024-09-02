import asyncio
import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
import pytest
from cogs.bank_cog import BankCog
from utils.bank_util import switch_token_emoji
# Set up an emoji cache for testing purposes
emoji_cache = {}


async def test_switch_token_emoji():
    # Create a mock bot object
    bot_mock = MagicMock()
    # Properly mock Discord emoji objects with 'name' attributes
    event_token_emoji = MagicMock(spec=discord.Emoji)
    event_token_emoji.name = "event_token"
    leadership_token_emoji = MagicMock(spec=discord.Emoji)
    leadership_token_emoji.name = "leadership_token"
    competitive_token_emoji = MagicMock(spec=discord.Emoji)
    competitive_token_emoji.name = "competitive_token"
    war_token_emoji = MagicMock(spec=discord.Emoji)
    war_token_emoji.name = "war_token"
    # Set the bot's emojis list to include the mocked emojis
    bot_mock.emojis = [event_token_emoji, leadership_token_emoji, competitive_token_emoji, war_token_emoji]
    # Call the function to test
    result = await switch_token_emoji(bot_mock, "Event Token")
    # Ensure the function returns the correct emoji name as a string
    assert result == "event_token", f"Expected 'event_token' but got {result}"


class TestBankCog(unittest.IsolatedAsyncioTestCase):  # Use IsolatedAsyncioTestCase for async tests

    def setUp(self):
        intents = discord.Intents.default()
        intents.message_content = True  # or any other intents you might need
        self.bot = commands.Bot(command_prefix="/", intents=intents)
        self.pool = AsyncMock()  # Mocking the connection pool
        self.cog = BankCog(self.bot, self.pool)
        self.ctx = AsyncMock(spec=commands.Context)
        self.ctx.guild = AsyncMock(spec=discord.Guild)
        self.ctx.author.guild_permissions.administrator = True
        self.user = AsyncMock(spec=discord.Member)
        self.user.id = 1234567890
        self.user.display_name = "TestUser"
        self.ctx.guild.member = [self.user]


    @patch ('cogs.bank_cog.openbank', new_callable=AsyncMock)
    async def test_ledger_no_tokens(self, mock_openbank):
        mock_openbank.return_value = {}  # Mock empty bank data
        self.ctx.send = AsyncMock()
        # Run the ledger command
        await self.cog.ledger(self, self.ctx, 'Event Token')
        # Capture the embed that was actually sent
        sent_embed = self.ctx.send.call_args[1]['embed']  # Access the embed argument in the actual call
        # Check that the embed contains the expected title and description
        assert sent_embed.title == "Good Company Ledger"  # Update to the correct title
        description = sent_embed.description if sent_embed.description is not None else ""
        assert "No members have any tokens in the bank for the Event Token type." in description
        assert len(sent_embed.fields) == 0  # Ensure no fields in the embed since it's an empty response


    @patch ('cogs.bank_cog.openbank', new_callable=AsyncMock)
    async def test_ledger_with_tokens(self, mock_openbank):
        testOfficer = AsyncMock(spec=discord.Member)
        testOfficer.display_name = "TestOfficer"
        testOfficer.id = 1234567891
        testOfficer.guild.member = [testOfficer]
        testUser = AsyncMock(spec=discord.Member)
        testUser.display_name = "TestUser"
        testUser.id = 1234567890
        member_dict = {
            testOfficer.id: testOfficer,
            testUser.id: testUser
        }
        self.ctx.guild.fetch_member = AsyncMock(side_effect=lambda member_id: member_dict.get(int(member_id)))
        mock_openbank.return_value = {
            'settler': {
                str(self.user.id): {
                    'Event Token': 10
                },
                str(testUser.id): {
                    'Event Token': 5
                }
            },
            'officer': {
                str(testOfficer.id): {
                    'Event Token': 5
                }
            }
        }
        await self.cog.ledger(self, self.ctx, 'Event Token')
        # Capture the embed that was sent
        sent_embed = self.ctx.send.call_args[1]['embed']
        # Check that the embed contains the expected title and fields
        self.assertEqual(sent_embed.title, "Good Company Ledger")
        self.assertTrue(any(field.name == "**Settler Balances**" and "TestUser's Event Token: 5" in field.value for field in sent_embed.fields))
        self.assertTrue(any(field.name == "**Officer Balances**" and "TestOfficer's Event Token: 5" in field.value for field in sent_embed.fields))



    @patch ('cogs.bank_cog.openbank', new_callable=AsyncMock)
    async def test_payout_no_tokens(self, mock_openbank):
        mock_openbank.return_value = {}  # Mock empty bank data
        self.ctx.send = AsyncMock()
        await self.cog.payout(self, self.ctx, income=1000.0)
        self.ctx.send.assert_called_with("No tokens have been earned this week. No payout necessary.")


    @patch ('os.makedirs')
    @patch ('cogs.bank_cog.openbank', new_callable=AsyncMock)
    async def test_payout_with_tokens(self, mock_openbank, mock_makedirs):
        # Mock roles
        settler_role = AsyncMock()
        settler_role.id = 1040383506481692693
        officer_role = AsyncMock()
        officer_role.id = 1040383501188468886
        # Mock user and assign roles
        testUser = AsyncMock(spec=discord.Member)
        testUser.display_name = "TestUser"
        testUser.id = 1234567890
        testUser.roles = [settler_role]
        # Mock context
        self.ctx.author.guild_permissions.administrator = True
        self.ctx.guild.members = [testUser]
        # Mock fetch_member to return TestUser based on id
        self.ctx.guild.fetch_member = AsyncMock(side_effect=lambda member_id: testUser if member_id == testUser.id else None)
        # Mock get_member to return TestUser based on id
        self.ctx.guild.get_member = AsyncMock(side_effect=lambda member_id: testUser if member_id == testUser.id else None)
        # Mock openbank to return a dictionary when awaited
        mock_openbank.return_value = {
            'settler': {
                str(testUser.id): {
                    'Event Token': 10,
                    'War Token': 5,
                    'Leadership Token': 3,
                    'Competitive Token': 2
                }
            }
        }
        with patch('cogs.bank_cog.savebank', new_callable=AsyncMock) as mock_savebank:
            await self.cog.payout(self, ctx=self.ctx, income=1000.0)
    # Assertions
        mock_savebank.assert_called_once_with(mock_openbank.return_value, self.pool)
        mock_makedirs.assert_called_once_with(
            'C:\\Users\\larry\\Desktop\\python update event bot\\weekly_payouts', exist_ok=True
        )


    @patch('cogs.bank_cog.openbank', new_callable=AsyncMock)
    async def test_balance(self, mock_openbank):
        # Set up mock data
        mock_openbank.return_value = {
            'settler': {
                str(self.user.id): {
                    'Event Token': 10,
                    'Leadership Token': 5,
                    'Competitive Token': 3,
                    'War Token': 1
                }
            }
        }
        await self.cog.balance(self, self.ctx, target=self.user)
        # Check if the balance command returns the correct balance
        self.ctx.send.assert_called_once()
        sent_embed = self.ctx.send.call_args[1]['embed']
        self.assertEqual(sent_embed.title, f"{self.user.display_name}'s current balances")
        # Include the emoji in the expected field name
        event_token_emoji = await switch_token_emoji(self.bot, "Event Token")
        expected_field_name = f"{event_token_emoji} Event Token Balance:"
        self.assertEqual(sent_embed.fields[0].name, expected_field_name)


    @patch('cogs.bank_cog.openbank', new_callable=AsyncMock)
    @patch('cogs.bank_cog.savebank', new_callable=AsyncMock)
    async def test_removetokens(self, mock_savebank, mock_openbank):
        # Initialize bank data
        bank_data = {
            'settler': {
                str(self.user.id): {
                    'Event Token': 10
                }
            }
        }
        # Set up mock_openbank to return the mutable bank_data dictionary
        mock_openbank.return_value = bank_data
        await self.cog.removetokens(self, self.ctx, self.user, 'Event Token', 5)
        # Verify the changes in the bank data
        self.assertEqual(bank_data['settler'][str(self.user.id)]['Event Token'], 5)
        # Ensure that savebank was called to persist the changes
        mock_savebank.assert_called_once_with(bank_data, self.pool)


if __name__ == "__main__":
    pytest.main()
