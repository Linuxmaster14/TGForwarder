import asyncio
import logging
import os
import argparse
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import PeerUser, PeerChat, PeerChannel

# Load environment variables
load_dotenv()

def setup_logging(disable_console=False):
    """Configure logging based on console preference."""
    if disable_console:
        # Only log to file, not console
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('telegram_forwarder.log'),
            ]
        )
    else:
        # Log to both console and file
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('telegram_forwarder.log')
            ]
        )

logger = logging.getLogger(__name__)

class TelegramForwarder:
    def __init__(self, remove_forward_signature=False):
        """Initialize the Telegram forwarder with environment variables."""
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.bot_token = os.getenv('BOT_TOKEN')
        self.source_id = os.getenv('SOURCE_ID')
        self.target_id = os.getenv('TARGET_ID')
        self.remove_forward_signature = remove_forward_signature
        
        # Validate required environment variables
        if not all([self.api_id, self.api_hash, self.source_id, self.target_id]):
            raise ValueError("Missing required environment variables. Check your .env file.")
        
        # Convert IDs to integers
        try:
            self.source_id = int(self.source_id)
            self.target_id = int(self.target_id)
        except ValueError:
            raise ValueError("SOURCE_ID and TARGET_ID must be valid integers.")
        
        # Initialize Telegram client
        if self.bot_token:
            # Bot mode
            self.client = TelegramClient('bot_session', self.api_id, self.api_hash)
            logger.info("Initialized in bot mode")
        else:
            # User mode
            self.client = TelegramClient('user_session', self.api_id, self.api_hash)
            logger.info("Initialized in user mode")
    
    async def start_client(self):
        """Start the Telegram client and handle authentication."""
        await self.client.start(bot_token=self.bot_token if self.bot_token else None)
        
        if not self.bot_token:
            # User authentication
            if not await self.client.is_user_authorized():
                phone = input("Enter your phone number: ")
                await self.client.send_code_request(phone)
                code = input("Enter the code you received: ")
                
                try:
                    await self.client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    password = input("Enter your 2FA password: ")
                    await self.client.sign_in(password=password)
        
        logger.info("Client started successfully")
    
    async def get_entity_info(self, entity_id):
        """Get information about an entity (user, chat, or channel)."""
        try:
            entity = await self.client.get_entity(entity_id)
            if hasattr(entity, 'title'):
                return f"{entity.title} (ID: {entity_id})"
            elif hasattr(entity, 'first_name'):
                name = entity.first_name
                if hasattr(entity, 'last_name') and entity.last_name:
                    name += f" {entity.last_name}"
                return f"{name} (ID: {entity_id})"
            else:
                return f"Entity (ID: {entity_id})"
        except Exception as e:
            logger.error(f"Error getting entity info for {entity_id}: {e}")
            return f"Unknown Entity (ID: {entity_id})"
    
    async def setup_forwarding(self):
        """Set up message forwarding from source to target."""
        # Get entity information for logging
        source_info = await self.get_entity_info(self.source_id)
        target_info = await self.get_entity_info(self.target_id)
        
        logger.info(f"Setting up forwarding from {source_info} to {target_info}")
        
        @self.client.on(events.NewMessage(chats=self.source_id))
        async def forward_handler(event):
            """Handle new messages and forward them."""
            try:
                # Get message details
                message = event.message
                sender_id = message.sender_id if message.sender_id else "Unknown"
                
                logger.info(f"Received message from {sender_id} in {source_info}")
                
                if self.remove_forward_signature:
                    # Send as new message without "Forward from..." signature
                    await self.client.send_message(
                        entity=self.target_id,
                        message=message.message,
                        file=message.media,
                        parse_mode='html' if message.entities else None
                    )
                    logger.info(f"Successfully sent message (without forward signature) to {target_info}")
                else:
                    # Forward the message with "Forward from..." signature
                    await self.client.forward_messages(
                        entity=self.target_id,
                        messages=message.id,
                        from_peer=self.source_id
                    )
                    logger.info(f"Successfully forwarded message to {target_info}")
                
            except FloodWaitError as e:
                logger.warning(f"Rate limited. Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Error forwarding message: {e}")
        
        logger.info("Message forwarding handler registered successfully")
    
    async def run(self):
        """Main method to run the forwarder."""
        try:
            await self.start_client()
            await self.setup_forwarding()
            
            logger.info("Telegram forwarder is now running. Press Ctrl+C to stop.")
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Stopping...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            await self.client.disconnect()
            logger.info("Client disconnected")

async def main():
    """Main function to run the application."""
    parser = argparse.ArgumentParser(description='Telegram Message Forwarder')
    parser.add_argument('--remove-forward-signature', '-r', action='store_true',
                        help='Remove "Forward from..." signature by sending as new messages instead of forwarding')
    parser.add_argument('--disable-console-log', '-q', action='store_true',
                        help='Disable console logging (only log to file)')
    
    args = parser.parse_args()
    
    # Setup logging based on arguments
    setup_logging(disable_console=args.disable_console_log)
    
    try:
        forwarder = TelegramForwarder(remove_forward_signature=args.remove_forward_signature)
        await forwarder.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print("\nPlease check your .env file and ensure all required variables are set.")
        print("You can use .env.example as a template.")
    except Exception as e:
        logger.error(f"Application error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
