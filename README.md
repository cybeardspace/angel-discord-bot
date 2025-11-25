# Angel – Quiet Alert Bot for Discord

Angel is a privacy-focused Discord bot that gives people a quiet, low-visibility way to alert moderators when they feel unsafe or are in a high-risk situation. It’s not a substitute for emergency services or professional help; it’s a discreet panic line for trusted staff.

---

## What Angel Does

• Provides one user command:  
    /angel  
    /angel message:<text>

• Sends a detailed embed to the configured moderator log channel.  
• Stores the user’s information in plain text (not only mentions).  
• Sends the user an ephemeral confirmation.  
• Leaves no visible message in channels.  
• Supports multiple servers, each with its own saved configuration.

Configuration is stored in angel_config.json.

---

## User Command

### /angel

Users can quietly request help.

Behavior:

• /angel with no message → alert with an empty message.  
• /angel message:<text> → includes the message in the embed.  
• If an intake channel is set, /angel only works there.  
• Used elsewhere → ephemeral “wrong channel” message.  
• Used correctly → ephemeral confirmation + embed sent to mods.

---

## Manager / Admin Commands

Angel considers the following as managers:

• Server owner  
• Anyone with the Manage Server permission  
• Anyone with a role designated as a manager role

---

### /angel_setup

    /angel_setup intake_channel:#channel mod_channel:#channel manager_role:@Role

Sets core configuration:

• intake channel  
• mod-log channel  
• designated manager role  

Adds the manager role to the list of allowed manager roles.

---

### /angel_set_intake

    /angel_set_intake channel:#channel

Sets which channel users must use for /angel.

---

### /angel_set_logs

    /angel_set_logs channel:#channel

Sets the moderator channel where Angel posts alert embeds.

---

### /angel_set_manager

    /angel_set_manager role:@Role allow:true
    /angel_set_manager role:@Role allow:false

Adds or removes a human role from the manager list.

Notes:

• Server owner + Manage Server users are always managers.  
• Manager roles only apply to human roles, not the bot role.

---

## Alert Embed Fields

Angel’s alert embed contains:

• User mention  
• Plain username  
• Display name  
• User ID  
• Channel used  
• Message text (if provided)

Plain username ensures logs remain readable if the user leaves the server.

---

## Roles and Permissions

Angel distinguishes two types:

### Bot Role – @angel

• Auto-created when the bot joins a server.  
• Should have access only to:  
    intake channel  
    mod-log channel  
• Needs permissions:  
    View Channel  
    Send Messages  
    Read Message History  
    Manage Messages  

### Manager Roles – Human

• Defined via /angel_setup or /angel_set_manager.  
• Hold management authority over Angel’s settings.

---

## Config Storage

angel_config.json contains per-guild:

• intake_channel_id  
• mod_channel_id  
• manager_role_ids  

It is loaded at startup and updated whenever settings change.  
.gitignore already excludes the file from source control.

---

## Discord Application Setup

In the Discord Developer Portal:

1. Create an application.  
2. Add a bot to it.  
3. Enable SERVER MEMBERS INTENT.  
4. Grant the bot these permissions:  
    View Channels  
    Send Messages  
    Read Message History  
    Manage Messages  
5. Under OAuth2 → URL Generator:  
    Scopes: bot, applications.commands  
    Same permissions as above  
6. Use the generated link to invite Angel to your server.

When joining a server, Angel creates and assigns its @angel role if needed.

---

## Per-Server Setup

After inviting Angel:

1. Choose an intake channel and a mod-log channel.  
2. Assign @angel access only to those two channels.  
3. Choose a manager role.  
4. Run:

        /angel_setup intake_channel:#intake mod_channel:#modlogs manager_role:@Moderator

5. Test /angel in the intake channel — user sees an ephemeral confirmation, mods see an embed.

---

## Running Angel

Angel expects the environment variable:

    DISCORD_BOT_TOKEN

Startup example:

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    export DISCORD_BOT_TOKEN="your-token"
    python angel.py

requirements.txt contains:

    discord.py==2.4.0

---

Angel’s purpose is simple: create a quiet, evidence-preserving line of communication that helps protect people without exposing them to additional risk.
