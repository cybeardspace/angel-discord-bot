import os
import json
from typing import Dict, Any

import discord
from discord import app_commands
from discord.ext import commands

# ==============================
# CONFIG STORAGE
# ==============================

CONFIG_FILE = "angel_config.json"
_config: Dict[str, Dict[str, Any]] = {}


def load_config() -> None:
    """Load per-guild configuration from disk."""
    global _config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                _config = json.load(f)
            except json.JSONDecodeError:
                _config = {}
    else:
        _config = {}


def save_config() -> None:
    """Save per-guild configuration to disk."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(_config, f, indent=2)


def get_guild_config(guild_id: int) -> Dict[str, Any]:
    """Return the config dict for a guild, creating defaults if needed."""
    gid = str(guild_id)
    if gid not in _config:
        _config[gid] = {
            "intake_channel_id": None,
            "mod_channel_id": None,
            "manager_role_ids": [],  # list of human role IDs allowed to manage
        }
    return _config[gid]


# ==============================
# PERMISSION CHECKS
# ==============================

def is_manager(interaction: discord.Interaction) -> bool:
    """Return True if the user is allowed to manage Angel settings."""
    guild = interaction.guild
    user = interaction.user

    if guild is None:
        return False

    # Guild owner always allowed
    if user.id == guild.owner_id:
        return True

    # Users with Manage Guild/Manage Server perms are allowed
    perms = getattr(user, "guild_permissions", None)
    if perms and perms.manage_guild:
        return True

    cfg = get_guild_config(guild.id)
    manager_role_ids = cfg.get("manager_role_ids", [])

    if not isinstance(user, discord.Member):
        return False

    return any(role.id in manager_role_ids for role in user.roles)


def manager_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_manager(interaction):
            raise app_commands.CheckFailure("You are not allowed to manage Angel settings.")
        return True

    return app_commands.check(predicate)


# ==============================
# BOT SETUP
# ==============================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # for guild.me, roles, etc.

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    load_config()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(f"Error syncing commands: {e}")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    When the bot joins a new guild, create an 'angel' role for the BOT to use.

    This role is for channel permission control (view/send/delete), NOT for human managers.
    Human managers are configured separately with /angel_set_manager or /angel_setup.
    """
    load_config()  # refresh in case

    # Check if role named 'angel' already exists (case-insensitive)
    angel_role = None
    for role in guild.roles:
        if role.name.lower() == "angel":
            angel_role = role
            break

    # If not, try to create it.
    # We give it the permissions the bot needs in channels where this role is allowed:
    # - view_channel, send_messages, read_message_history, manage_messages.
    if angel_role is None:
        perms = discord.Permissions(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
        )
        try:
            angel_role = await guild.create_role(
                name="angel",
                permissions=perms,
                reason="Role for the Angel bot to control its channel permissions.",
            )
            print(f"Created 'angel' role in guild {guild.name} ({guild.id}).")
        except discord.Forbidden:
            print(
                f"Could not create 'angel' role in guild {guild.name} ({guild.id}) "
                f"due to missing permissions."
            )
            angel_role = None
        except Exception as e:
            print(
                f"Unexpected error creating 'angel' role in guild {guild.name} ({guild.id}): {e}"
            )
            angel_role = None

    # Assign the angel role to the bot itself, if possible
    if angel_role is not None:
        try:
            me: discord.Member = guild.me  # the bot's member object in this guild
            if me is not None and angel_role not in me.roles:
                await me.add_roles(
                    angel_role,
                    reason="Angel bot role for channel permissions.",
                )
                print(
                    f"Assigned 'angel' role to bot in guild {guild.name} ({guild.id})."
                )
        except discord.Forbidden:
            print(
                f"Could not assign 'angel' role to bot in guild {guild.name} ({guild.id}) "
                f"due to missing permissions."
            )
        except Exception as e:
            print(
                f"Unexpected error assigning 'angel' role to bot in guild {guild.name} ({guild.id}): {e}"
            )


# ==============================
# CORE ALERT HANDLER
# ==============================

async def angel_alert(interaction: discord.Interaction, message: str | None):
    """Core logic for sending an alert to mods."""
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or channel is None:
        await interaction.response.send_message(
            "This command can only be used inside a server channel.",
            ephemeral=True,
        )
        return

    cfg = get_guild_config(guild.id)
    intake_channel_id = cfg.get("intake_channel_id")
    mod_channel_id = cfg.get("mod_channel_id")

    # Must have a mod channel configured
    if not mod_channel_id:
        await interaction.response.send_message(
            "The alert system is not fully configured yet. "
            "Please let a moderator know.",
            ephemeral=True,
        )
        return

    # If an intake channel is configured, enforce it
    if intake_channel_id and channel.id != intake_channel_id:
        await interaction.response.send_message(
            "This isn’t the right place to use that command.\n"
            "Please use it in the designated help channel.",
            ephemeral=True,
        )
        return

    user = interaction.user

    # Capture identity info as PLAIN TEXT so it survives if they leave
    raw_id = user.id
    base_username = user.name

    if hasattr(user, "discriminator") and user.discriminator not in (None, "", "0"):
        classic_username = f"{user.name}#{user.discriminator}"
    else:
        classic_username = user.name

    global_name = getattr(user, "global_name", None)
    display_name = getattr(user, "display_name", user.name)

    content = message.strip() if message else "(no message)"

    # Build log text
    log_lines = [
        "🚨 /angel alert triggered",
        f"Guild: {guild.name} (ID: {guild.id})",
        "",
        f"User ID: {raw_id}",
        f"Base username: {base_username}",
        f"Classic username: {classic_username}",
        f"Global name at time of alert: {global_name if global_name else '(none)'}",
        f"Server display name at time of alert: {display_name}",
        "",
        f"Channel: #{channel.name} (ID: {channel.id})",
        "",
        "Message:",
        content,
    ]
    log_text = "\n".join(log_lines)

    mod_channel = bot.get_channel(mod_channel_id)

    if mod_channel is None:
        await interaction.response.send_message(
            "Something went wrong notifying the moderators. "
            "Please tell a moderator if you can.",
            ephemeral=True,
        )
        return

    # Send alert to mods
    await mod_channel.send(log_text)

    # Try to clean up any visible trace in the channel (best-effort; slash commands usually don't leave a normal message)
    try:
        if isinstance(channel, discord.TextChannel):
            msg = await channel.fetch_message(interaction.id)
            await msg.delete()
    except Exception:
        pass

    # Ephemeral confirmation (viewer-only, dismissable)
    await interaction.response.send_message(
        "Your alert has been sent to the moderation team.\n"
        "Nothing from this command is visible to others in the channel.\n"
        "This message is only visible to you.",
        ephemeral=True,
    )


# ==============================
# /angel — alert
# ==============================

@bot.tree.command(
    name="angel",
    description="Send a quiet alert to the moderation team."
)
@app_commands.describe(
    message="Optional short message for the moderators (can be left empty)."
)
async def angel_root(interaction: discord.Interaction, message: str | None = None):
    """Always behave as the alert command, for all users."""
    await angel_alert(interaction, message)


# ==============================
# /angel_info
# ==============================

@bot.tree.command(
    name="angel_info",
    description="Show information about the Angel alert system."
)
async def angel_info(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    cfg = get_guild_config(guild.id)
    intake_id = cfg.get("intake_channel_id")
    mod_id = cfg.get("mod_channel_id")

    intake_text = f"<#{intake_id}>" if intake_id else "(not set)"
    mod_text = f"<#{mod_id}>" if mod_id else "(not set)"

    user_help = (
        "**Angel Alert System**\n"
        "This system provides a quiet way to alert the moderation team.\n\n"
        "**To send an alert:**\n"
        "`/angel` — sends an alert with no text.\n"
        "`/angel message: <text>` — sends an alert with a short message.\n\n"
        "**What happens:**\n"
        "• Your alert goes directly to the mod team.\n"
        "• The command leaves no public trace in the channel.\n"
        "• You get a private confirmation message only you can see.\n"
    )

    if is_manager(interaction):
        manager_help = (
            "\n**Current configuration (you have manager permissions):**\n"
            f"• Intake channel: {intake_text}\n"
            f"• Mod alert channel: {mod_text}\n\n"
            "**Manager commands:**\n"
            "`/angel_set_intake <channel>`\n"
            "`/angel_set_logs <channel>`\n"
            "`/angel_set_manager <role>`\n"
            "`/angel_setup <intake> <logs> <manager role>`\n"
        )
        await interaction.response.send_message(
            user_help + manager_help,
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            user_help,
            ephemeral=True,
        )


# ==============================
# MANAGEMENT COMMANDS
# ==============================

@bot.tree.command(
    name="angel_set_intake",
    description="Set the channel where /angel may be used."
)
@manager_only()
@app_commands.describe(
    channel="Channel where users will run /angel."
)
async def angel_set_intake(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    cfg = get_guild_config(guild.id)
    cfg["intake_channel_id"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"Intake channel set to #{channel.name} (ID: {channel.id}).",
        ephemeral=True,
    )


@bot.tree.command(
    name="angel_set_logs",
    description="Set the mod channel where alerts are sent."
)
@manager_only()
@app_commands.describe(
    channel="Channel where mod alerts will be sent."
)
async def angel_set_logs(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    cfg = get_guild_config(guild.id)
    cfg["mod_channel_id"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"Mod alert / logs channel set to #{channel.name} (ID: {channel.id}).",
        ephemeral=True,
    )


@bot.tree.command(
    name="angel_set_manager",
    description="Set the role allowed to manage Angel settings."
)
@manager_only()
@app_commands.describe(
    role="Human role that can manage Angel settings."
)
async def angel_set_manager_role(
    interaction: discord.Interaction,
    role: discord.Role,
):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    cfg = get_guild_config(guild.id)
    cfg["manager_role_ids"] = [role.id]
    save_config()

    await interaction.response.send_message(
        f"Manager role set to @{role.name} (ID: {role.id}).\n"
        "Guild owner and users with Manage Server are always allowed as well.",
        ephemeral=True,
    )


@bot.tree.command(
    name="angel_setup",
    description="Run full Angel setup: intake, logs, and manager role."
)
@manager_only()
@app_commands.describe(
    intake_channel="Channel where users will run /angel.",
    mod_channel="Channel where alerts should be sent for mods.",
    manager_role="Human role that can manage Angel settings.",
)
async def angel_setup(
    interaction: discord.Interaction,
    intake_channel: discord.TextChannel,
    mod_channel: discord.TextChannel,
    manager_role: discord.Role,
):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    cfg = get_guild_config(guild.id)
    cfg["intake_channel_id"] = intake_channel.id
    cfg["mod_channel_id"] = mod_channel.id
    cfg["manager_role_ids"] = [manager_role.id]
    save_config()

    await interaction.response.send_message(
        "Angel setup completed:\n"
        f"• Intake channel: #{intake_channel.name} (ID: {intake_channel.id})\n"
        f"• Mod alert channel: #{mod_channel.name} (ID: {mod_channel.id})\n"
        f"• Manager role: @{manager_role.name} (ID: {manager_role.id})",
        ephemeral=True,
    )


# ==============================
# RUN BOT
# ==============================

if __name__ == "__main__":
    load_config()
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is not set.")
    bot.run(token)
