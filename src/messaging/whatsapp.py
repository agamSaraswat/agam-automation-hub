"""
WhatsApp integration — TODO STUB.

This file is scaffolded for future WhatsApp integration.
Wire it up when ready without restructuring the repo.

TODO:
  - Evaluate options:
    a) WhatsApp Business API (requires Meta business verification)
    b) Twilio WhatsApp API (paid, but easier setup)
    c) whatsapp-web.js via a Node.js sidecar (free, unofficial)
  - Add WHATSAPP_* credentials to .env
  - Implement message send/receive handlers
  - Mirror Telegram bot commands
  - Add to scheduler/cron.py for briefing delivery
"""

import logging

logger = logging.getLogger(__name__)


def send_whatsapp_message(phone: str, text: str) -> None:
    """Send a WhatsApp message. TODO: implement."""
    raise NotImplementedError(
        "WhatsApp integration is not yet implemented. "
        "See src/messaging/whatsapp.py for scaffolding instructions."
    )


def start_whatsapp_listener() -> None:
    """Start listening for WhatsApp messages. TODO: implement."""
    raise NotImplementedError("WhatsApp listener not yet implemented.")


if __name__ == "__main__":
    print("WhatsApp integration is a TODO stub. Not yet implemented.")
