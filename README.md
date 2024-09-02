# Good Kompany's Event Bot

A versatile and customizable Discord bot designed to manage events, handle user tokens, and interact with members in engaging ways. It comes with powerful features such as event lifecycle management, token payouts, database management, and much more, providing a complete solution for Discord communities.

## Features

- **Event Management:** Handles event creation, participation tracking, and event finalization.
- **Token Management:** Distributes different types of tokens (Event, Leadership, Competitive, War) based on member participation, and event type using Event Description in Discord.
- **Database Integration:** Utilizes an asynchronous database pool for efficient data management.
- **Custom Commands:** Provides various commands for users and admins to interact with the bot.
- **Logging and Error Handling:** Comprehensive logging and error handling to ensure smooth operation.

## Requirements

- Python 3.8 or higher
- `discord.py` library
- `aiomysql` library for asynchronous MySQL interaction
- `python-dotenv` for environment variable management

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/Sauseda15/good-company-event-bot.git
    cd good-company-event-bot
    ```

2. **Create a Virtual Environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the Required Packages:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
DISCORD_TOKEN=your_discord_bot_token
DBHOST=your_database_host
DBPORT=3306 # Default MySQL port
DBUSER=your_database_user
DBPASSWORD=your_database_password
DBNAME=your_database_name
EVENT_CHANNEL=your_event_channel_id
VODS_CHANNEL=your_vods_channel_id
```


## Database Setup

Ensure that your MySQL database is set up and accessible with the credentials provided in the .env file. The bot will automatically create the necessary tables upon startup if they do not exist.

# Running the Bot

Run the bot with:
```bash
python main.py
```

The bot should now be online and running in your specified Discord server.

## Commands
1. User Commands: 
    - /balance - Check your token balance.
2. Admin Commands
    - /addtokens @user <token_type> - Adds tokens to a user's balance.
    - /removetokens @user <token_type> - Removes tokens from a user's balance.
    - /payout - Distributes payouts based on tokens earned.


## Contact
- For questions or support, please open an issue on this repository.