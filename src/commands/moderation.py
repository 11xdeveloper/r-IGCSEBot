from bot import bot, discord, pymongo, datetime, time, commands
from commands.dms import send_dm
from utils.bans import is_banned
from utils.roles import is_chat_moderator, is_moderator, is_admin
from utils.mongodb import gpdb, punishdb, ipdb
from utils.constants import GUILD_ID, LINK


def convert_time(time: tuple[str, str, str, str]) -> str:
    time_str = ""
    if time[0] != "0":
        time_str += f"{time[0]} day{'s' if int(time[0]) > 1 else ''} "
    if time[1] != "0":
        time_str += f"{time[1]} hour{'s' if int(time[1]) > 1 else ''} "
    if time[2] != "0":
        time_str += f"{time[2]} min{'s' if int(time[2]) > 1 else ''} "
    return time_str.strip()


@bot.slash_command(description="Check a user's previous offenses (warns/timeouts/bans)")
async def history(
    interaction: discord.Interaction,
    user: discord.User = discord.SlashOption(
        name="user", description="User to view history of", required=True
    ),
):
    if not await is_moderator(interaction.user) and not await is_chat_moderator(
        interaction.user
    ):
        await interaction.send(
            "You are not permitted to use this command.", ephemeral=True
        )
    await interaction.response.defer()
    actions = {}
    history = []
    total = 0
    allowed_actions_for_total = ["Warn", "Timeout", "Mute", "Ban", "Kick"]
    results = punishdb.get_punishments_by_user(user.id)
    for result in results:

        if result["action"] not in actions:
            actions[result["action"]] = 1
        else:
            actions[result["action"]] += 1

        if result["action"] in allowed_actions_for_total:
            total += 1
        if isinstance(result["when"], datetime.datetime):
            date_of_event = result["when"].strftime("%d %b, %Y at %I:%M %p")
        else:
            date_of_event = datetime.datetime.fromisoformat(
                str(result["when"])
            ).strftime("%d %b, %Y at %I:%M %p")
        duration_as_text = (
            f" ({result['duration']})" if result["action"] == "Timeout" else ""
        )

        reason = f" for {result['reason']}" if result["reason"] else ""

        try:
            if "#" not in result["action_by"] and result["action_by"].isnumeric():
                moderator = interaction.guild.get_member(
                    int(result["action_by"])
                ) or await interaction.guild.fetch_member(int(result["action_by"]))
                moderator = moderator.name
            else:
                moderator = result["action_by"].strip()
        except discord.errors.NotFound:
            moderator = result["action_by"].strip()

        final_string = f"[{date_of_event}] {result['action']}{duration_as_text}{reason} by {moderator.strip()}"
        history.append(final_string)

    if len(history) == 0:
        await interaction.send(
            f"{user} does not have any previous offenses.", ephemeral=False
        )
    else:
        result = ipdb.infraction_points.find_one(
            {"user_id": user.id, "guild_id": interaction.guild.id}
        )

        if result is None:
            points = 0
        else:
            points = result.points

        text = f"Moderation History for {user}:\n\nNo. of offences ({total}):\n"
        text += "\n".join(list(map(lambda x: f"{x[0]}: {x[1]}", list(actions.items()))))
        text += "\n"
        text += "\nFurther Details:\n"
        text += ("\n".join(history))[:1900]
        text += f"\nTotal Points: {f"{points} - Mods Review & Take appropriate action" if points >= 10 else f"{points}"}"
        await interaction.send(f"```{text}```", ephemeral=False)


@bot.slash_command(description="Warn a user (for mods)")
async def warn(
    interaction: discord.Interaction,
    user: discord.Member = discord.SlashOption(
        name="user", description="User to warn", required=True
    ),
    reason: str = discord.SlashOption(
        name="reason", description="Reason for warn", required=True
    ),
):

    action_type = "Warn"
    mod = interaction.user
    if await is_banned(user, interaction.guild):
        await interaction.send("User is banned from the server!", ephemeral=True)
        return
    if not await is_moderator(interaction.user) and not await is_chat_moderator(
        interaction.user
    ):
        await interaction.send(
            f"Sorry {mod}, you don't have the permission to perform this action.",
            ephemeral=True,
        )
        return
    await interaction.response.defer()
    warnlog_channel = gpdb.get_pref("warnlog_channel", interaction.guild.id)
    if warnlog_channel:
        ban_msg_channel = bot.get_channel(warnlog_channel)
        try:
            last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
            case_no = (
                int(
                    "".join(
                        list(
                            filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])
                        )
                    )
                )
                + 1
            )
        except Exception:
            case_no = 1
        ban_msg = f"""Case #{case_no} | [{action_type}]\nUsername: {str(user)} ({user.id})\nModerator: {mod} \nReason: {reason}"""
        await interaction.send(f"{str(user)} has been warned.")
        await ban_msg_channel.send(ban_msg)
    await send_dm(
        user,
        content=f'You have been warned in r/IGCSE by moderator {mod} for "{reason}".\n\nPlease be mindful in your further interaction in the server to avoid further action being taken against you, such as a timeout or a ban.',
    )
    punishdb.add_punishment(case_no, user.id, interaction.user.id, reason, action_type)
    ipdb.set(user.id, interaction.guild.id, 1)


@bot.slash_command(description="Timeout a user (for mods)")
async def timeout(
    interaction: discord.Interaction,
    user: discord.Member = discord.SlashOption(
        name="user", description="User to timeout", required=True
    ),
    time_: str = discord.SlashOption(
        name="duration",
        description="Duration of timeout (e.g. 1d5h) up to 28 days (use 'permanent')",
        required=True,
    ),
    reason: str = discord.SlashOption(
        name="reason", description="Reason for timeout", required=True
    ),
):
    action_type = "Timeout"
    mod = interaction.user.mention
    if await is_banned(user, interaction.guild):
        await interaction.send("User is banned from the server!", ephemeral=True)
        return
    if not await is_moderator(interaction.user) and not await is_chat_moderator(
        interaction.user
    ):
        await interaction.send(
            f"Sorry {mod}, you don't have the permission to perform this action.",
            ephemeral=True,
        )
        return
    await interaction.response.defer()

    lowered_time = time_.lower()
    if lowered_time in ["unspecified", "permanent", "undecided"]:
        seconds = 86400 * 28
    else:
        seconds = 0
        for (
            character
        ) in (
            time_
        ):  # Side effect of this is that 9d9d or 10h10h would work, but that's fine?
            match character:
                case "d":
                    seconds += int(time_.split("d")[0]) * 86400
                case "h":
                    seconds += int(time_.split("h")[0]) * 3600
                case "m":
                    seconds += int(time_.split("m")[0]) * 60
                case "s":
                    seconds += int(time_.split("s")[0])

    if seconds == 0:
        await interaction.send("You can't timeout for zero seconds!", ephemeral=True)
        return
    await user.edit(timeout=datetime.timedelta(seconds=seconds))
    human_readable_time = f"{seconds // 86400}d {(seconds % 86400) // 3600}h {(seconds % 3600) // 60}m {seconds % 60}s"
    ban_msg_channel = bot.get_channel(
        gpdb.get_pref("modlog_channel", interaction.guild.id)
    )
    if ban_msg_channel:
        try:
            last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
            case_no = (
                int(
                    "".join(
                        list(
                            filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])
                        )
                    )
                )
                + 1
            )
        except Exception:
            case_no = 1
        ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {str(user)} ({user.id})
Moderator: {mod}
Reason: {reason}
Duration: {human_readable_time}
Until: <t:{int(time.time()) + seconds}> (<t:{int(time.time()) + seconds}:R>)"""
        await ban_msg_channel.send(ban_msg)
    await send_dm(
        user,
        content=f"""You have been given a timeout on the r/IGCSE server
Reason: {reason}
Duration: {human_readable_time}
Until: <t:{int(time.time()) + seconds}> (<t:{int(time.time()) + seconds}:R>)""",
    )
    await interaction.send(
        f"{str(user)} has been put on time out until <t:{int(time.time()) + seconds}>, which is <t:{int(time.time()) + seconds}:R>."
    )
    timeout_duration_simple = convert_time(
        (
            str(seconds // 86400),
            str((seconds % 86400) // 3600),
            str((seconds % 3600) // 60),
            str(seconds % 60),
        )
    )
    punishdb.add_punishment(
        case_no,
        user.id,
        interaction.user.id,
        reason,
        action_type,
        duration=timeout_duration_simple,
    )

    if seconds >= 604800:
        points = 4
    elif seconds >= 21600:
        points = 3
    else:
        points = 2

    ipdb.set(user.id, interaction.guild.id, points)


@bot.slash_command(description="Untimeout a user (for mods)")
async def untimeout(
    interaction: discord.Interaction,
    user: discord.Member = discord.SlashOption(
        name="user", description="User to untimeout", required=True
    ),
):
    action_type = "Remove Timeout"
    mod = interaction.user.mention
    if await is_banned(user, interaction.guild):
        await interaction.send("User is banned from the server!", ephemeral=True)
        return
    if not await is_moderator(interaction.user) and not await is_chat_moderator(
        interaction.user
    ):
        await interaction.send(
            f"Sorry {mod}, you don't have the permission to perform this action.",
            ephemeral=True,
        )
        return
    await interaction.response.defer()
    await user.edit(timeout=None)
    ban_msg_channel = bot.get_channel(
        gpdb.get_pref("modlog_channel", interaction.guild.id)
    )
    if ban_msg_channel:
        try:
            last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
            case_no = (
                int(
                    "".join(
                        list(
                            filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])
                        )
                    )
                )
                + 1
            )
        except Exception:
            case_no = 1
        ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {str(user)} ({user.id})
Moderator: {mod}"""
        await ban_msg_channel.send(ban_msg)
    await interaction.send(f"Timeout has been removed from {str(user)}.")
    punishdb.add_punishment(case_no, user.id, interaction.user.id, "", action_type)


@bot.slash_command(description="Kick a user from the server (for mods)")
async def kick(
    interaction: discord.Interaction,
    user: discord.Member = discord.SlashOption(
        name="user", description="User to kick", required=True
    ),
    reason: str = discord.SlashOption(
        name="reason", description="Reason for kick", required=True
    ),
):
    action_type = "Kick"
    mod = interaction.user.mention
    if not await is_moderator(interaction.user):
        await interaction.send(
            f"Sorry {mod}, you don't have the permission to perform this action.",
            ephemeral=True,
        )
        return
    if await is_banned(user, interaction.guild):
        await interaction.send("User is banned from the server!", ephemeral=True)
        return
    await interaction.response.defer()
    try:
        await user.send(
            f"Hi there from {interaction.guild.name}. You have been kicked from the server due to '{reason}'."
        )
    except Exception:
        pass
    ban_msg_channel = bot.get_channel(
        gpdb.get_pref("modlog_channel", interaction.guild.id)
    )
    if ban_msg_channel:
        try:
            last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
            case_no = (
                int(
                    "".join(
                        list(
                            filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])
                        )
                    )
                )
                + 1
            )
        except Exception:
            case_no = 1
        ban_msg = f"""Case #{case_no} | [{action_type}]\nUsername: {str(user)} ({user.id})\nModerator: {mod} \nReason: {reason}"""
        await ban_msg_channel.send(ban_msg)
    await interaction.guild.kick(user)
    await interaction.send(f"{str(user)} has been kicked.")
    punishdb.add_punishment(case_no, user.id, interaction.user.id, reason, action_type)


@bot.slash_command(description="Ban a user from the server (for mods)")
async def ban(
    interaction: discord.Interaction,
    user: discord.Member = discord.SlashOption(
        name="user", description="User to ban", required=True
    ),
    reason: str = discord.SlashOption(
        name="reason", description="Reason for ban", required=True
    ),
    delete_message_days: int = discord.SlashOption(
        name="delete_messages",
        choices={
            "Don't Delete Messages": 0,
            "Delete Today's Messages": 1,
            "Delete 3 Days of Messages": 3,
            "Delete 1 Week of Messages": 7,
        },
        default=0,
        description="Duration of messages from the user to delete (defaults to zero)",
        required=False,
    ),
):
    action_type = "Ban"
    mod = interaction.user.mention

    if type(user) is not discord.Member:
        await interaction.send("User is not a member of the server", ephemeral=True)
        return
    if not await is_moderator(interaction.user):
        await interaction.send(
            f"Sorry {mod}, you don't have the permission to perform this action.",
            ephemeral=True,
        )
        return
    if await is_banned(user, interaction.guild):
        await interaction.send("User is banned from the server!", ephemeral=True)
        return
    if user.id == interaction.user.id:
        await interaction.send(
            "Well, why do you wanna ban yourself? Just leave!", ephemeral=True
        )
        return
    await interaction.response.defer()
    try:
        if interaction.guild.id == GUILD_ID:
            await user.send(
                f"Hi there from {interaction.guild.name}. You have been banned from the server due to '{reason}'. If you feel this ban was done in error, to appeal your ban, please fill the form below.\nhttps://forms.gle/8qnWpSFbLDLdntdt8"
            )
        else:
            await user.send(
                f"Hi there from {interaction.guild.name}. You have been banned from the server due to '{reason}'."
            )
    except Exception:
        pass
    ban_msg_channel = bot.get_channel(
        gpdb.get_pref("modlog_channel", interaction.guild.id)
    )
    if ban_msg_channel:
        try:
            last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
            case_no = (
                int(
                    "".join(
                        list(
                            filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])
                        )
                    )
                )
                + 1
            )
        except Exception:
            case_no = 1
        ban_msg = f"""Case #{case_no} | [{action_type}]\nUsername: {str(user)} ({user.id})\nModerator: {mod} \nReason: {reason}"""
        await ban_msg_channel.send(ban_msg)
    await interaction.guild.ban(user, delete_message_days=delete_message_days)
    await interaction.send(f"{str(user)} has been banned.")
    punishdb.add_punishment(case_no, user.id, interaction.user.id, reason, action_type)


@bot.slash_command(description="Unban a user from the server (for mods)")
async def unban(
    interaction: discord.Interaction,
    user: discord.User = discord.SlashOption(
        name="user", description="User to unban", required=True
    ),
):
    action_type = "Unban"
    mod = interaction.user.mention
    if not await is_moderator(interaction.user):
        await interaction.send(
            f"Sorry {mod}, you don't have the permission to perform this action.",
            ephemeral=True,
        )
        return
    await interaction.response.defer()
    await interaction.guild.unban(user)
    await interaction.send(f"{str(user)} has been unbanned.")

    ban_msg_channel = bot.get_channel(
        gpdb.get_pref("modlog_channel", interaction.guild.id)
    )
    if ban_msg_channel:
        try:
            last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
            case_no = (
                int(
                    "".join(
                        list(
                            filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])
                        )
                    )
                )
                + 1
            )
        except Exception:
            case_no = 1
        ban_msg = f"""Case #{case_no} | [{action_type}]\nUsername: {str(user)} ({user.id})\nModerator: {mod}"""
        await ban_msg_channel.send(ban_msg)
        punishdb.add_punishment(case_no, user.id, interaction.user.id, "", action_type)


class PunishmentsSelect(discord.ui.Select):
    def __init__(self, results: list[dict]):
        super().__init__(
            placeholder="Select a punishment to remove", min_values=1, max_values=1
        )
        self.results = results
        for result in self.results:
            self.add_option(
                label=f"Case #{result.get('case_id', "0000")} | {result['action']} - {result['reason']}",
                value=str(result["_id"]),
            )


class PunishmentsView(discord.ui.View):
    def __init__(self, results: list[dict]):
        super().__init__()
        self.results = results
        self.select = PunishmentsSelect(results)
        self.add_item(self.select)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, row=2)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if not self.select.values or len(self.select.values) == 0:
            await interaction.edit(
                content="Well, you need to select something for me to delete it, don't you? So do it!"
            )
            return

        punishdb.remove_punishment(self.select.values[0])

        await interaction.edit(content="Punishment removed!", view=None)
        for child in self.children:
            child.disabled = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=2)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = True
        await interaction.edit(content="Cancelled!", view=None)
        self.stop()


@bot.slash_command(description="Remove infraction (for admins)")
async def remove_infraction(
    interaction: discord.Interaction,
    user: discord.User = discord.SlashOption(
        name="user", description="User to remove infraction from", required=True
    ),
):
    if not await is_admin(interaction.user):
        await interaction.send(
            "You are not permitted to use this command.", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    results = punishdb.get_punishments_by_user(user.id)
    results = list(results)
    if len(results) == 0:
        await interaction.send(f"{user} does not have any previous offenses.")
        return

    view = PunishmentsView(results)
    await interaction.send(view=view, ephemeral=True)


@bot.slash_command(
    name="infraction_points", description="Get the infraction points of a user"
)
@commands.guild_only()
async def infraction_points(
    interaction: discord.Interaction,
    user: discord.Member = discord.SlashOption(
        name="user", description="The user to get the infraction points of"
    ),
):
    user = ipdb.infraction_points.find_one(
        {"guild_id": interaction.guild.id, "user_id": user.id}
    )

    await interaction.send(
        f"{user.mention} has no infraction points"
        if user is None
        else f"{user.mention} has {user['points']} infraction points"
    )
