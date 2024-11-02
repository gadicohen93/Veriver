from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import errors
import os
from typing import Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TelegramAuthManager:
    def __init__(self, session_dir: str = ".sessions"):
        """
        Initialize the Telegram authentication manager.

        Args:
            session_dir: Directory to store session files
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)

        # Load credentials from environment variables if available
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone = os.getenv("TELEGRAM_PHONE")
        self.username = os.getenv("TELEGRAM_USERNAME")

        self.client: Optional[TelegramClient] = None
        self.session_file = self.session_dir / "telegram.session"

    async def initialize_client(self) -> Tuple[bool, str]:
        """
        Initialize the Telegram client with stored or provided credentials.

        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            if not all([self.api_id, self.api_hash]):
                return (
                    False,
                    "API credentials not found. Please set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables.",
                )

            # Create the client
            self.client = TelegramClient(
                str(self.session_file), self.api_id, self.api_hash
            )

            # Try to start and check authorization
            await self.client.start()

            if not await self.client.is_user_authorized():
                return False, "User not authorized. Please call login() method."

            return True, "Client initialized successfully"

        except Exception as e:
            logger.error(f"Error initializing client: {e}")
            return False, f"Failed to initialize client: {str(e)}"

    async def login(
        self, phone: Optional[str] = None, code_callback=None
    ) -> Tuple[bool, str]:
        """
        Handle the login process with phone number and verification code.

        Args:
            phone: Phone number to use for login
            code_callback: Optional callback function to get verification code

        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            if not self.client:
                return False, "Client not initialized. Call initialize_client() first."

            phone = phone or self.phone
            if not phone:
                return False, "Phone number required for login"

            # Request verification code
            await self.client.send_code_request(phone)

            # Get the verification code
            if code_callback:
                code = await code_callback()
            else:
                code = input("Enter the code you received: ")

            # Sign in with the code
            await self.client.sign_in(phone, code)

            return True, "Login successful"

        except errors.SessionPasswordNeededError:
            # 2FA handling
            if not self.client:
                return False, "Client not initialized"

            try:
                password = input(
                    "Two-factor authentication enabled. Please enter your password: "
                )
                await self.client.sign_in(password=password)
                return True, "2FA login successful"
            except Exception as e:
                return False, f"2FA login failed: {str(e)}"

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, f"Login failed: {str(e)}"

    async def subscribe_to_channel(self, channel: str) -> Tuple[bool, str]:
        """
        Subscribe to a Telegram channel.

        Args:
            channel: Channel username or invite link

        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            if not self.client:
                return False, "Client not initialized"

            if not await self.client.is_user_authorized():
                return False, "User not authorized"

            # Handle different channel format inputs
            if channel.startswith("https://t.me/"):
                channel = channel.split("/")[-1]
            elif channel.startswith("@"):
                channel = channel[1:]

            # Try to join the channel
            await self.client(JoinChannelRequest(channel))
            return True, f"Successfully subscribed to {channel}"

        except errors.FloodWaitError as e:
            return False, f"Too many requests. Please wait {e.seconds} seconds"
        except Exception as e:
            logger.error(f"Channel subscription error: {e}")
            return False, f"Failed to subscribe: {str(e)}"

    async def close(self):
        """Close the Telegram client connection."""
        if self.client:
            await self.client.disconnect()
            self.client = None
