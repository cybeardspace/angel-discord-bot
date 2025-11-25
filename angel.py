import os

import json

from typing import Dict, Any, Optional



import discord

from discord import app_commands

from discord.ext import commands



# ==============================

# CONFIG STORAGE

# ==============================



CONFIG_FILE = "angel_config.json"

_config: Dict[str, Dict[str, Any]] = {}





def load_config() -> None:

    """Load configuration from disk."""

    global _config

    if not os.path.exists(CONFIG_FILE):

        _config = {}

        return

    try:

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:

            _config = json.load(f)

    except Exception:

        _config = {}





def save_config() -> None:

    """Persist configuration to disk."""

    try:

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:

            json.dump(_config, f, indent=2)

    except Exception:

        # Failing to save config shouldn't crash the bot.

        pass





def get_guild_config(guild_id: int) -> Dict[str, Any]:

    """Return a config dict for the given guild, creating default if needed."""

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



    # Harden against weird / partial member data:

    roles = getattr(user, "roles", []) or []

    return any(

        isinstance(role, discord.Role) and role.id in manager_role_ids

        for role in roles

    )





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

intents.members = True  # needed for role-based checks



bot = commands.Bot(

    command_prefix="!",

    intents=intents,

    help_command=None,

)



tree = bot.tree





@bot.event

async def on_ready():

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    print("------")



    # Sync slash commands

    try:

        await tree.sync()

        print("Slash commands synced.")

    except Exception as e:

        print(f"Error syncing commands: {e}")





@bot.event

async def on_guild_join(guild: discord.Guild):

    """Try to create and assign an 'angel' role for the bot."""

    try:

        # Check if role already exists

        role = discord.utils.get(guild.roles, name="angel")

        if role is None:

            role = await guild.create_role(

                name="angel",

                reason="Role for angel safety bot",

            )

        # Assign the role to the bot, if we see our own Member

        me = guild.me  # type: ignore[attr-defined]

        if me and role not in me.roles:

            await me.add_roles(role, reason="Granting angel bot role")

    except discord.Forbidden:

        # No perms to manage roles; fine, server owner can sort it out.

        pass

    except Exception:

        pass





# ==============================

# CORE SAFEWORD COMMAND

# ==============================



@tree.command(name="angel", description="Quietly request help from trusted moderators.")

@app_commands.describe(

    message="Optional context about what you need help with."

)

async def angel_command(interaction: discord.Interaction, message: Optional[str] = None):

    """

    Main safeword command.



    /angel

    /angel message:<optional text>

    """

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(

            "This command can only be used in a server.",

            ephemeral=True,

        )

        return



    cfg = get_guild_config(guild.id)

    intake_channel_id = cfg.get("intake_channel_id")

    mod_channel_id = cfg.get("mod_channel_id")



    # Check that the command is run in the correct channel (if configured).

    if intake_channel_id is not None and interaction.channel_id != intake_channel_id:

        await interaction.response.send_message(

            "This isn't the right place to use /angel. "

            "Use it in the designated intake channel.",

            ephemeral=True,

        )

        return



    # Normalize message so None and "" behave the same

    message = message or ""



    # Always acknowledge to the user first, ephemerally.

    try:

        await interaction.response.send_message(

            "Your request has been quietly sent to the moderators. Someone will reach out soon.",

            ephemeral=True,

        )

    except discord.InteractionResponded:

        # In case something already responded, just skip.

        pass



    # If mod channel is configured, post there with context.

    if mod_channel_id is not None:

        channel = guild.get_channel(mod_channel_id)

        if isinstance(channel, discord.TextChannel):

            # Build evidence-friendly identity strings

            raw_name = getattr(interaction.user, "name", None) or str(interaction.user)

            discrim = getattr(interaction.user, "discriminator", None)

            if discrim and discrim != "0":

                plain_username = f"{raw_name}#{discrim}"

            else:

                plain_username = raw_name



            display_name = getattr(interaction.user, "display_name", plain_username)



            embed = discord.Embed(

                title="� Angel Safeword Triggered",

                description=(

                    f"User (mention): {interaction.user.mention}\n"

                    f"User (plain): {plain_username}\n"

                    f"Display name: {display_name}\n"

                    f"User ID: {interaction.user.id}\n"

                    f"Channel: {interaction.channel.mention if interaction.channel else 'Unknown'}\n"

                ),

                color=discord.Color.red(),

            )

            if message:

                embed.add_field(name="Message", value=message, inline=False)



            try:

                await channel.send(embed=embed)

            except discord.Forbidden:

                # Can't post to mod channel, nothing else to do quietly

                pass





# ==============================

# ADMIN / MANAGER COMMANDS

# ==============================



@tree.command(name="angel_setup", description="Do initial setup for Angel (intake, logs, manager).")

@manager_only()

@app_commands.describe(

    intake_channel="Channel where users will invoke /angel.",

    mod_channel="Channel where Angel will notify moderators.",

    manager_role="Role that should be allowed to manage Angel settings.",

)

async def angel_setup(

    interaction: discord.Interaction,

    intake_channel: discord.TextChannel,

    mod_channel: discord.TextChannel,

    manager_role: discord.Role,

):

    """

    One-shot setup:



    /angel_setup intake_channel:#get-help mod_channel:#angel-logs manager_role:@Admin

    """

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(

            "This command can only be used in a server.",

            ephemeral=True,

        )

        return



    cfg = get_guild_config(guild.id)

    cfg["intake_channel_id"] = intake_channel.id

    cfg["mod_channel_id"] = mod_channel.id



    manager_role_ids = cfg.get("manager_role_ids", [])

    if manager_role.id not in manager_role_ids:

        manager_role_ids.append(manager_role.id)

    cfg["manager_role_ids"] = manager_role_ids



    save_config()



    await interaction.response.send_message(

        (

            "Angel setup complete:\n"

            f"- Intake channel: {intake_channel.mention}\n"

            f"- Mod log channel: {mod_channel.mention}\n"

            f"- Manager role added: {manager_role.mention}"

        ),

        ephemeral=True,

    )





@tree.command(name="angel_set_intake", description="Set the intake channel for /angel requests.")

@manager_only()

@app_commands.describe(channel="Channel where users should run /angel.")

async def angel_set_intake(interaction: discord.Interaction, channel: discord.TextChannel):

    """

    /angel_set_intake channel:#get-help

    """

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(

            "This command can only be used in a server.",

            ephemeral=True,

        )

        return



    cfg = get_guild_config(guild.id)

    cfg["intake_channel_id"] = channel.id

    save_config()



    await interaction.response.send_message(

        f"Intake channel set to {channel.mention}.",

        ephemeral=True,

    )





@tree.command(name="angel_set_logs", description="Set the moderator log channel for Angel alerts.")

@manager_only()

@app_commands.describe(channel="Channel where Angel should post alerts for moderators.")

async def angel_set_logs(interaction: discord.Interaction, channel: discord.TextChannel):

    """

    /angel_set_logs channel:#angel-logs

    """

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(

            "This command can only be used in a server.",

            ephemeral=True,

        )

        return



    cfg = get_guild_config(guild.id)

    cfg["mod_channel_id"] = channel.id

    save_config()



    await interaction.response.send_message(

        f"Moderator log channel set to {channel.mention}.",

        ephemeral=True,

    )





@tree.command(name="angel_set_manager", description="Add or remove human roles allowed to manage Angel.")

@manager_only()

@app_commands.describe(

    role="The role to grant or revoke Angel manager permissions.",

    allow="Whether this role should be allowed to manage Angel (True) or disallowed (False).",

)

async def angel_set_manager(

    interaction: discord.Interaction,

    role: discord.Role,

    allow: bool,

):

    """

    /angel_set_manager role:@Admin allow:true|false

    """

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(

            "This command can only be used in a server.",

            ephemeral=True,

        )

        return



    cfg = get_guild_config(guild.id)

    manager_role_ids = cfg.get("manager_role_ids", [])



    if allow:

        if role.id not in manager_role_ids:

            manager_role_ids.append(role.id)

    else:

        if role.id in manager_role_ids:

            manager_role_ids.remove(role.id)



    cfg["manager_role_ids"] = manager_role_ids

    save_config()



    verb = "now allowed to" if allow else "no longer allowed to"

    await interaction.response.send_message(

        f"Role {role.mention} is {verb} manage Angel settings.",

        ephemeral=True,

    )





# ==============================

# ERROR HANDLING

# ==============================



@tree.error

async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):

    if isinstance(error, app_commands.CheckFailure):

        try:

            await interaction.response.send_message(

                "You are not allowed to use this command.",

                ephemeral=True,

            )

        except discord.InteractionResponded:

            await interaction.followup.send(

                "You are not allowed to use this command.",

                ephemeral=True,

            )

        return



    # Generic error: keep it vague to the user, log to console.

    print(f"App command error in {interaction.command}: {error!r}")

    try:

        await interaction.response.send_message(

            "Something went wrong while running that command.",

            ephemeral=True,

        )

    except discord.InteractionResponded:

        await interaction.followup.send(

            "Something went wrong while running that command.",

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
