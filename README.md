Discord Bot README
Good Kompany's Event Bot

Description
This bot is a versatile and customizable Discord bot designed to manage events, handle user tokens, and interact with members in various engaging ways. It comes with powerful features such as event lifecycle management, token payouts, database management, and much more, providing a complete solution for Discord communities.

Features
Event Management: Handles event creation, participation tracking, and event finalization.
Token Management: Distributes different types of tokens (Event, Leadership, Competitive, War) based on member participation.
Database Integration: Utilizes an asynchronous database pool for efficient data management.
Custom Commands: Provides various commands for users and admins to interact with the bot.
Logging and Error Handling: Comprehensive logging and error handling to ensure smooth operation.

Requirements
Python 3.8 or higher
discord.py library
aiomysql library for asynchronous MySQL interaction
python-dotenv for environment variable management
Installation
Clone the Repository

bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
Install the Required Packages

bash
Copy code
pip install -r requirements.txt
Configuration
Environment Variables

Create a .env file in the root directory with the following variables:

env
DISCORD_TOKEN=your_discord_bot_token
DBHOST=your_database_host
DBPORT=3306  # Default MySQL port
DBUSER=your_database_user
DBPASSWORD=your_database_password
DBNAME=your_database_name
EVENT_CHANNEL=your_event_channel_id
VODS_CHANNEL=your_vods_channel_id
Replace your_discord_bot_token and other placeholders with your actual configuration details.

Database Setup

Ensure that your MySQL database is set up and accessible with the credentials provided in the .env file. The bot will automatically create the necessary tables upon startup if they do not exist.

Running the Bot
Run the Bot

bash
python main.py
The bot should now be online and running in your specified Discord server.

Commands
User Commands
/balance - Check your token balance.
/join - Join an ongoing event.
Admin Commands
/start_event - Starts a new event.
/end_event - Ends an ongoing event and processes results.
/addtokens @user <token_type> <amount> - Adds tokens to a user's balance.
/removetokens @user <token_type> <amount> - Removes tokens from a user's balance.
/payout  - Distributes payouts based on tokens earned.
Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a new branch (git checkout -b feature/YourFeature).
Commit your changes (git commit -am 'Add some feature').
Push to the branch (git push origin feature/YourFeature).
Create a new Pull Request.

License
This project is licensed under the MIT License - see the LICENSE file for details.

Contact
For questions or support, please open an issue on this repository.