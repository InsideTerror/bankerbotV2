# 📢 Broadcast System Documentation

The broadcast system allows World Bank Officers to send messages to economy servers through a ticket-based interface.

## 🎯 Overview

The system provides five types of broadcasts:
1. **Pending Applications** - Message servers with pending economy applications
2. **Approved Servers** - Message all approved economy servers
3. **All Economy Servers** - Message all servers in the economy system (pending, approved, rejected)
4. **ALL Bot Servers** - Message every server the bot is in, regardless of economy status
5. **Specific Server** - Message a single server by name (command-based)

## 🚀 Initial Setup

### Step 1: Run Setup Command

In your Central Bank server's approval channel, run:

```
!setup_broadcast
```

This will create three persistent message panels with buttons for each broadcast type.

**Requirements:**
- Must be run by the bot owner
- Must be run in the Central Bank server
- Bot needs permissions to send messages and embeds

### What Gets Created:

1. **Four Message Panels** - Each with a button to create a broadcast ticket
   - Pending Applications (Orange)
   - Approved Servers (Green)
   - All Economy Servers (Blue)
   - ALL Bot Servers (Red - use with caution!)
2. **Broadcast Messages Storage** - Saved to `broadcast_messages.json`
3. **Broadcast Log File** - All broadcasts logged to `broadcast_log.txt`

## 📝 How to Use

### Using Ticket-Based Broadcasts

#### Step 1: Click the Button
- Go to the Central Bank approval channel
- Choose the appropriate broadcast type:
  - **Pending Applications** - Only servers with pending economy applications
  - **Approved Servers** - Only approved economy servers
  - **All Economy Servers** - All servers in the economy (pending, approved, rejected)
  - **ALL Bot Servers** - ⚠️ EVERY server the bot is in (use sparingly!)
- Click the "Create Broadcast Ticket" button
- A new private channel will be created for you

#### Step 2: Compose Your Message
- The bot will greet you with instructions
- Simply type your message in the ticket channel
- The message can be as long as you need

#### Step 3: Confirm and Send
- The bot will show you a confirmation with:
  - Target type (pending/approved/all)
  - Number of recipients
  - Preview of your message
  - List of recipient servers
- Click "Confirm & Send" to broadcast
- Or click "Cancel" to write a new message

#### Step 4: Automatic Cleanup
- The bot sends your message to all target servers
- Shows you a completion report (sent/failed)
- Ticket channel automatically deletes after 30 seconds

### Using Specific Server Broadcast (Command)

For sending to a single specific server, use the command:

```
!broadcast_server "Server Name" Your message content here
```

**Examples:**
```
!broadcast_server "Medieval Kingdom" Hello! This is a test message.

!broadcast_server "Space Station RP" We have updated our economy policies, please review them.
```

**Notes:**
- Server name must be in quotes
- Server name is case-insensitive
- Message is sent immediately without confirmation
- Still logged to broadcast_log.txt

## 🔄 Automatic Maintenance

### Daily Message Check

The bot automatically checks every 24 hours if the broadcast panel messages still exist.

**If a message is deleted:**
1. Bot detects it's missing
2. Recreates the message with button
3. Updates the stored message ID
4. Continues normal operation

**This ensures:**
- Panels are always available
- Accidental deletions don't break the system
- No manual intervention needed

## 📊 Logging

All broadcasts are logged to `broadcast_log.txt` with:
- Timestamp (UTC)
- Officer name and ID
- Target type
- Number of recipients
- Message preview (first 100 characters)

**Example log entry:**
```
[2025-01-02T15:30:45.123456] Officer: JohnDoe#1234 (123456789) | Target: approved | Recipients: 15 | Message: Hello everyone! We have some exciting updates to share about our economy system...
```

## 🎛️ Features

### Ticket System
- **Private Channels**: Each broadcast gets its own temporary channel
- **Officer Only**: Only the officer who created it can use the ticket
- **Auto-Delete**: Channels are removed after broadcast completes
- **Category Organization**: Tickets created in "📢 Broadcast Tickets" category

### Message Delivery
- **Smart Channel Selection**: Bot finds the best channel to post in each server
  - Prioritizes: general, announcements, economy, updates
  - Falls back to first available channel with send permissions
- **Embed Format**: Messages sent as professional embeds
- **Rate Limiting**: 0.5s delay between sends to avoid Discord limits
- **Error Handling**: Failed sends are tracked and reported

### Confirmation System
- **Preview**: See exactly what will be sent
- **Recipient List**: View which servers will receive the message
- **Cancel Option**: Change your mind before sending
- **No Accidental Sends**: Requires explicit confirmation

## 🛠️ Commands Reference

### Officer Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `!setup_broadcast` | Initialize the broadcast system | `!setup_broadcast` |
| `!broadcast_server` | Send to specific server | `!broadcast_server "Name" message` |
| `!close_ticket` | Close current broadcast ticket | `!close_ticket` |

### Button Actions

| Button | Where | What It Does |
|--------|-------|--------------|
| Create Broadcast Ticket | Broadcast panels | Opens a new ticket channel |
| Confirm & Send | Ticket confirmation | Sends the broadcast |
| Cancel | Ticket confirmation | Cancels and allows rewrite |

## 📋 Best Practices

### Writing Effective Broadcasts

1. **Be Clear and Concise**
   - Get to the point quickly
   - Use proper formatting
   - Include action items if needed

2. **Choose the Right Target**
   - **Pending:** For application-related communication
   - **Approved:** For economy participants only
   - **All Economy:** For everyone who has applied (any status)
   - **ALL Bot Servers:** For critical announcements to every server (⚠️ use sparingly!)
   - **Specific:** For individual server matters

3. **Timing Matters**
   - Avoid broadcasting during off-peak hours
   - Give servers time to respond if action is needed
   - Don't spam with frequent messages

### Security Considerations

1. **Officer Verification**
   - Only authorized officers can create tickets
   - Only ticket owner can confirm/cancel
   - All actions are logged

2. **Message Review**
   - Always preview before confirming
   - Check recipient count
   - Verify target type

3. **Error Recovery**
   - Failed sends are reported
   - Original ticket preserved for reference
   - Logs maintained for audit

## 🔍 Troubleshooting

### Broadcast panels disappeared
**Solution:** Run `!setup_broadcast` again to recreate them

### Can't create ticket
**Possible causes:**
- Not a World Bank Officer
- Bot lacks channel creation permissions
- Server reached channel limit

**Solution:** Check officer status with `list officers` command via DM

### Message failed to send to some servers
**Common reasons:**
- Bot not in the server
- No accessible channels
- Permissions missing

**Check:** The completion report shows which servers failed and why

### Ticket won't close
**Solution:** Use `!close_ticket` command or wait for auto-deletion after broadcast

### Messages not in right channel
**Note:** Bot automatically selects best available channel. Server admins can rename channels to influence selection:
- Name a channel "economy" or "announcements" for priority

## 📊 Files Created

| File | Purpose | Location |
|------|---------|----------|
| `broadcast_messages.json` | Stores panel message IDs | Root directory |
| `broadcast_log.txt` | Logs all broadcasts | Root directory |

Both files are automatically created on first use.

## 🎓 Example Workflow

### Scenario: Announcing Policy Update

1. **Officer logs into Discord**
2. **Goes to Central Bank approval channel**
3. **Clicks "Create Broadcast Ticket" under "Approved Servers"**
4. **Bot creates private ticket channel**
5. **Officer types:**
   ```
   📢 Policy Update
   
   Effective immediately, transfer limits have been updated:
   - Minimum: 10 currency units
   - Maximum: 500,000 currency units
   
   This helps prevent abuse while allowing legitimate transfers.
   Questions? Contact a World Bank Officer.
   ```
6. **Bot shows confirmation with 15 recipient servers**
7. **Officer clicks "Confirm & Send"**
8. **Bot broadcasts to all 15 servers**
9. **Shows report: 14 sent, 1 failed (bot not in server)**
10. **Ticket auto-deletes after 30 seconds**
11. **Broadcast logged to broadcast_log.txt**

### Scenario: Following Up with Specific Server

1. **Officer wants to message just "Space Station RP"**
2. **Types in any channel:**
   ```
   !broadcast_server "Space Station RP" Thank you for updating your application! Your economy has been approved.
   ```
3. **Bot immediately sends message**
4. **Officer gets confirmation**
5. **Logged to broadcast_log.txt**

## 🔐 Permissions Required

### Bot Permissions Needed:
- Manage Channels (create/delete tickets)
- Send Messages (send broadcasts)
- Embed Links (formatted messages)
- Read Message History (ticket management)

### Officer Permissions:
- Must be added as World Bank Officer
- Or be the bot owner

---

**Questions or issues?** Check the logs or contact the bot owner.
