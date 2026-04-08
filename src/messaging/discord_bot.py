"""
Discord bot integration — TODO STUB.

This file is scaffolded for future Discord integration.
Wire it up when ready without restructuring the repo.

TODO:
  - Install discord.py: pip install discord.py
  - Create Discord bot at https://discord.com/developers/applications
  - Add DISCORD_BOT_TOKEN to .env
  - Implement slash commands mirroring Telegram bot functionality
  - Add to scheduler/cron.py
"""

import logging

logger = logging.getLogger(__name__)


def start_discord_bot() -> None:
    """Start the Discord bot. TODO: implement."""
    raise NotImplementedError(
        "Discord bot is not yet implemented. "
        "See src/messaging/discord_bot.py for scaffolding instructions."
    )


# TODO: Implement these handlers
# async def cmd_briefing(interaction): ...
# async def cmd_jobs(interaction): ...
# async def cmd_linkedin(interaction): ...
# async def cmd_status(interaction): ...
# async def handle_message(message): ...


if __name__ == "__main__":
    print("Discord bot is a TODO stub. Not yet implemented.")
