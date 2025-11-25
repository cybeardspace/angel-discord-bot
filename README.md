# Angel – Quiet Alert Bot for Discord

Angel is a small, privacy-focused Discord bot that gives people a **quiet way to alert moderators** when they might be in danger or in a high-risk situation (e.g., domestic abuse, stalking, unsafe home environments).

It is **not** a replacement for emergency services, legal advice, or professional counseling. It’s just a tiny, careful piece of infrastructure: a panic cord that pings your mod team.

---

## What Angel Does

- Provides a **single user command**:

  - `/angel` – sends an alert with no text.  
  - `/angel message: <text>` – sends an alert with a short note.

- For each alert:

  - Sends a detailed log to a **mod-only channel**.
  - Stores the user’s name(s) and ID as plain **text** (not just a mention), so the alert is still readable even if they leave or get forced out.
  - Leaves no public trace in the channel (slash commands are invisible by default; the bot also tries to delete any fallback message).
  - Sends an **ephemeral confirmation** only the user can see.

- Supports **multiple servers**: each guild has its own configuration.

---

## Commands

### User commands

- `/angel`  
  Send a quiet alert to the moderation team.  

  - `/angel` → alert with “(no message)”  
  - `/angel message: I only have a second` → alert with text  

- `/angel_info`  
  Shows a short explanation of how Angel works.  
  If you’re a manager, it also shows the current config and admin commands.

---

### Manager/admin commands

Angel’s idea of “manager”:

- server owner, or  
- anyone with “Manage Server”, or  
- anyone with a role set via `/angel_set_manager`.

Commands:

- `/angel_setup intake_channel:#channel mod_channel:#channel manager_role:@Role`  
  One-shot setup for the server:

  - intake channel = where users are allowed to run `/angel`  
  - mod channel = where Angel sends alerts  
  - manager role = human role allowed to configure Angel

- `/angel_set_intake #channel`  
  Set the intake channel where `/angel` may be used.

- `/angel_set_logs #channel`  
  Set the mod log/alert channel for incoming alerts.

- `/angel_set_manager @role`  
  Choose which **human** role can manage Angel’s settings.

---

## Roles and Permissions

Angel distinguishes two things:

### 1. Bot role – `@angel`

- Created **automatically** when the bot joins a server (if it doesn’t already exist).
- Assigned to the bot only.
- Given base guild-level permissions:

  - View Channels  
  - Send Messages  
  - Read Message History  
  - Manage Messages  

Server owners should then **control where** the `@angel` role is allowed via channel permission overwrites:

- Give `@angel` access only to:
  - the intake channel (e.g., `#project-angel`), and
  - the mod alert/log channel.

### 2. Manager role – human

- Selected via `/angel_set_manager` or `/angel_setup`.
- Any existing role (e.g., `@Moderator`, `@Admin`).
- People with this role can run:

  - `/angel_setup`  
  - `/angel_set_intake`  
  - `/angel_set_logs`  
  - `/angel_set_manager`  
  - and they see extra info in `/angel_info`.

---

## Discord Application Setup

You only do this **once**, in the Discord Developer Portal.

1. Go to: https://discord.com/developers/applications  
2. Click “New Application” → name it (e.g. “AngelBot”).  
3. Go to **Bot** tab:
   - Click “Add Bot”.
   - Under **Privileged Gateway Intents**, enable:
     - `SERVER MEMBERS INTENT`.
   - Under **Bot Permissions**, enable at least:
     - ✅ View Channels  
     - ✅ Send Messages  
     - ✅ Read Message History  
     - ✅ Manage Messages  

4. Go to **OAuth2 → URL Generator**:
   - Scopes:
     - ✅ `bot`  
     - ✅ `applications.commands`
   - Under **Bot Permissions**, again select:
     - ✅ View Channels  
     - ✅ Send Messages  
     - ✅ Read Message History  
     - ✅ Manage Messages  

   Copy the generated invite URL.

5. Use that URL to **invite Angel** to any server.

When Angel joins a server, it will:

- auto-create an `@angel` role (if needed),  
- assign that role to itself,  
- then wait for you to configure channels/manager.

---

## Per-Server Setup

Once Angel is in a server:

1. Decide on:
   - An **intake channel** (where users will run `/angel`, e.g. `#project-angel`).  
   - A **mod alert/log channel** (e.g. `#mod-angel-alerts`).  
   - A **manager role** (e.g. `@Moderator`).

2. In Discord channel permissions:

   For the intake + mod channels, give the `@angel` role:

   - View Channel  
   - Send Messages  
   - Read Message History  
   - Manage Messages (recommended so Angel can delete any visible traces)

3. As server owner, or someone with “Manage Server” (or your chosen manager role), run:

   ```text
   /angel_setup intake_channel:#project-angel mod_channel:#mod-angel-alerts manager_role:@Moderator
