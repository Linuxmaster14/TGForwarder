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
        self.remove_forward_signature = remove_forward_signature
        
        # Check for legacy single source/target configuration
        self.source_id = os.getenv('SOURCE_ID')
        self.target_id = os.getenv('TARGET_ID')
        self.forwarding_rules = os.getenv('FORWARDING_RULES')
        
        # Validate required environment variables
        if not all([self.api_id, self.api_hash]):
            raise ValueError("Missing API_ID or API_HASH. Check your .env file.")
        
        # Parse forwarding configuration
        self.forwarding_map = self._parse_forwarding_rules()
        
        if not self.forwarding_map:
            raise ValueError("No forwarding rules configured. Set either SOURCE_ID/TARGET_ID or FORWARDING_RULES.")
        
        # Initialize Telegram client
        if self.bot_token:
            # Bot mode
            self.client = TelegramClient('bot_session', self.api_id, self.api_hash)
            logger.info("Initialized in bot mode")
        else:
            # User mode
            self.client = TelegramClient('user_session', self.api_id, self.api_hash)
            logger.info("Initialized in user mode")
    
    def _parse_forwarding_rules(self):
        """Parse forwarding rules from environment variables."""
        forwarding_map = {}
        
        # Check for legacy single source/target configuration
        if self.source_id and self.target_id:
            try:
                source_id = int(self.source_id)
                target_id = int(self.target_id)
                forwarding_map[source_id] = [target_id]
                logger.info("Using legacy single source/target configuration")
                return forwarding_map
            except ValueError:
                raise ValueError("SOURCE_ID and TARGET_ID must be valid integers.")
        
        # Parse new multiple forwarding rules
        if self.forwarding_rules:
            try:
                # Format: source1:target1:target2,source2:target3,source3:target4
                rules = self.forwarding_rules.split(',')
                for rule in rules:
                    rule = rule.strip()
                    if not rule:
                        continue
                    
                    parts = rule.split(':')
                    if len(parts) < 2:
                        raise ValueError(f"Invalid forwarding rule format: {rule}")
                    
                    source_id = int(parts[0])
                    target_ids = [int(target) for target in parts[1:]]
                    
                    if source_id in forwarding_map:
                        # Extend existing targets for this source
                        forwarding_map[source_id].extend(target_ids)
                    else:
                        forwarding_map[source_id] = target_ids
                
                logger.info(f"Parsed {len(forwarding_map)} forwarding rules")
                return forwarding_map
                
            except ValueError as e:
                raise ValueError(f"Error parsing FORWARDING_RULES: {e}")
        
        return {}
    
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
        """Set up message forwarding from multiple sources to their respective targets."""
        # Log all forwarding rules
        logger.info("Setting up forwarding rules:")
        for source_id, target_ids in self.forwarding_map.items():
            source_info = await self.get_entity_info(source_id)
            target_infos = []
            for target_id in target_ids:
                target_info = await self.get_entity_info(target_id)
                target_infos.append(target_info)
            logger.info(f"  {source_info} -> {', '.join(target_infos)}")
        
        # Get all source IDs for the event handler
        source_ids = list(self.forwarding_map.keys())
        
        @self.client.on(events.NewMessage(chats=source_ids))
        async def forward_handler(event):
            """Handle new messages and forward them to configured targets."""
            try:
                # Get message details
                message = event.message
                source_id = event.chat_id
                sender_id = message.sender_id if message.sender_id else "Unknown"
                
                # Get target IDs for this source
                target_ids = self.forwarding_map.get(source_id, [])
                if not target_ids:
                    logger.warning(f"No targets configured for source {source_id}")
                    return
                
                source_info = await self.get_entity_info(source_id)
                logger.info(f"Received message from {sender_id} in {source_info}")
                
                # Forward to all configured targets
                for target_id in target_ids:
                    try:
                        target_info = await self.get_entity_info(target_id)
                        
                        if self.remove_forward_signature:
                            # Send as new message without "Forward from..." signature
                            await self.client.send_message(
                                entity=target_id,
                                message=message.message,
                                file=message.media,
                                parse_mode='html' if message.entities else None
                            )
                            logger.info(f"Successfully sent message (without forward signature) to {target_info}")
                        else:
                            # Forward the message with "Forward from..." signature
                            await self.client.forward_messages(
                                entity=target_id,
                                messages=message.id,
                                from_peer=source_id
                            )
                            logger.info(f"Successfully forwarded message to {target_info}")
                            
                    except Exception as e:
                        target_info = await self.get_entity_info(target_id)
                        logger.error(f"Error forwarding to {target_info}: {e}")
                
            except FloodWaitError as e:
                logger.warning(f"Rate limited. Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Error in forward handler: {e}")
        
        logger.info("Message forwarding handlers registered successfully")
    
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
