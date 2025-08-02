# Telegram Forwarder

A Python script using Telethon to automatically forward messages from a source chat/group/channel to a target destination.

## Features

- Forward messages from any Telegram chat, group, or channel
- Support for both user accounts and bot accounts
- Automatic handling of rate limits
- Comprehensive logging
- Easy configuration via environment variables

## Prerequisites

1. **Telegram API Credentials**: Get your `api_id` and `api_hash` from [https://my.telegram.org](https://my.telegram.org)
2. **Bot Token** (optional): If you want to use a bot account, get a bot token from [@BotFather](https://t.me/BotFather)
3. **Chat IDs**: You need the IDs of the source and target chats/groups/channels

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd TGForwarder
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on the example:
```bash
cp .env.example .env
```

4. Edit the `.env` file and fill in your credentials:
```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here  # Optional, for bot mode
SOURCE_ID=your_source_chat_id
TARGET_ID=your_target_chat_id
```

## Getting Chat IDs

To find chat IDs, you can:

1. **For private chats**: Use the user's ID (positive number)
2. **For groups/channels**: Use the negative ID format
   - For groups: `-100` + group ID (e.g., `-1001234567890`)
   - For channels: `-100` + channel ID (e.g., `-1001234567890`)

You can use tools like [@userinfobot](https://t.me/userinfobot) or [@get_id_bot](https://t.me/get_id_bot) to get chat IDs.

## Usage

Run the script with various options:

```bash
# Basic usage
python telegram_forwarder.py

# Remove "Forward from..." signature (sends as new messages)
python telegram_forwarder.py --remove-forward-signature

# Disable console logging (only log to file)
python telegram_forwarder.py --disable-console-log

# Use both options
python telegram_forwarder.py -r -q
```

### Command Line Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--remove-forward-signature` | `-r` | Remove "Forward from..." signature by sending as new messages instead of forwarding |
| `--disable-console-log` | `-q` | Disable console logging (only log to telegram_forwarder.log file) |

### First Run

- **User Mode**: If you're not using a bot token, you'll be prompted to enter your phone number and verification code
- **Bot Mode**: If you provided a bot token, the script will start immediately

The script will run continuously and forward any new messages from the source to the target.

## Configuration Options

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_ID` | Yes | Your Telegram API ID |
| `API_HASH` | Yes | Your Telegram API Hash |
| `BOT_TOKEN` | No | Bot token for bot mode (leave empty for user mode) |
| `SOURCE_ID` | Yes | ID of the source chat/group/channel |
| `TARGET_ID` | Yes | ID of the target chat/group/channel |

### User Mode vs Bot Mode

- **User Mode**: Uses your personal Telegram account. Can access any chat you're a member of.
- **Bot Mode**: Uses a bot account. The bot must be added to both source and target chats with appropriate permissions.

## Important Notes

1. **Rate Limits**: The script automatically handles Telegram's rate limits
2. **Permissions**: Ensure the account/bot has necessary permissions in both source and target chats
3. **Privacy**: Be mindful of privacy and legal considerations when forwarding messages
4. **Session Files**: The script creates session files (`user_session.session` or `bot_session.session`) to avoid re-authentication

## Logging

The script provides detailed logging including:
- Connection status
- Message forwarding events
- Error handling
- Rate limit notifications

### Log Output
- **Default**: Logs to both console and `telegram_forwarder.log` file
- **Quiet mode** (`-q` flag): Logs only to `telegram_forwarder.log` file

### Forward Signature Options
- **Default**: Messages are forwarded with "Forward from..." signature
- **Remove signature** (`-r` flag): Messages are sent as new messages without the forward signature

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Check your API credentials
2. **Permission Denied**: Ensure the account/bot has access to both chats
3. **Invalid Chat ID**: Verify the chat IDs are correct
4. **Rate Limited**: The script handles this automatically, but frequent rate limits may indicate too much activity

### Error Messages

- `Missing required environment variables`: Check your `.env` file
- `SOURCE_ID and TARGET_ID must be valid integers`: Ensure IDs are numbers
- `Error getting entity info`: The account/bot cannot access the specified chat

## License

This project is licensed under the terms specified in the [`LICENSE`](./LICENSE) file.

## Author

Made with [Linuxmaster14](https://github.com/Linuxmaster14)

## Disclaimer

This tool is for educational and personal use. Please respect Telegram's Terms of Service and applicable laws regarding message forwarding and privacy.
