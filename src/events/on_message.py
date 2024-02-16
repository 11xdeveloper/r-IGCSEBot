from utils.constants import (
    BETA,
    GUILD_ID,
    SHOULD_LOG_ALL,
    BOTLOG_CHANNEL_ID,
    MODMAIL_LOGS_ID,
    FORUMTHREAD_ID,
    CREATEDM_ID,
    BOTUPDATES_CHANNEL,
)
from utils.data import REP_DISABLE_CHANNELS
from bot import discord, bot, keywords
import sys
from utils.mongodb import gpdb, smdb, repdb, kwdb, asmdb
from utils.roles import is_moderator, is_helper, is_chat_moderator, is_bot_developer


async def get_thread(message: discord.Message, is_dm: bool):
    member_id: int = 0
    if is_dm:
        member_id = message.author.id
    else:
        member_id = int(message.content)

    guild = bot.get_guild(GUILD_ID)
    member = guild.get_member(member_id)
    channel = guild.get_channel(FORUMTHREAD_ID)
    newmsg_channel = guild.get_channel(MODMAIL_LOGS_ID)
    threads = channel.threads
    thread_name = f"{member_id}"
    thread = discord.utils.get(threads, name=thread_name)

    if is_dm:
        if thread is None:
            thread = await channel.create_thread(
                name=thread_name,
                content=f"Username: `{member.name}`\nUser ID: `{member_id}`",
            )
            embed = discord.Embed(
                title="New DM Recieved",
                description=f"Username: `{member.name}`\nUser ID: `{member_id}`\nThread: {thread.mention}",
                color=0xFF3E00,
            )
            await newmsg_channel.send(embed=embed)
            return thread
        else:
            embed = discord.Embed(
                title="New Message Recieved",
                description=f"Username: `{member.name}`\nUser ID: `{member_id}`\nThread: {thread.mention}",
                color=0x8DD5A2,
            )
            await newmsg_channel.send(embed=embed)
            return thread
    else:
        if thread is None:
            thread = await channel.create_thread(
                name=thread_name,
                content=f"Username: `{member.name}`\nUser ID: `{member_id}`",
            )
            await message.reply(f"DM Channel has been created at {thread.mention}!")
            return thread
        else:
            await message.reply(
                f"DM Channel already exists for that user at {thread.mention}!"
            )
            return thread


async def counting(message: discord.Message):
    if message.author.bot:
        await message.delete()
        return

    msgs = await message.channel.history(limit=2).flatten()
    try:
        msg = msgs[1]

        if "✅" in [str(reaction.emoji) for reaction in msg.reactions]:
            last_number = int(msg.content)
            last_author = msg.author
        else:
            last_number = 0
            last_author = None
    except Exception:
        last_number = 0
        last_author = None

    try:
        if int(message.content) == last_number + 1 and last_author != message.author:
            await message.add_reaction("✅")
        else:
            await message.delete()
    except Exception:
        await message.delete()


async def is_welcome(text: str):
    alternatives = ["you're welcome", "your welcome", "ur welcome", "no problem"]
    alternatives_2 = ["np", "np!", "yw", "yw!"]
    lowercase = text.lower()
    if "welcome" == lowercase:
        return True
    else:
        for alternative in alternatives:
            if alternative in lowercase:
                return True
        for alternative in alternatives_2:
            if alternative in lowercase.split() or alternative == lowercase:
                return True
    return False


async def is_thanks(text: str):
    alternatives = [
        "thanks",
        "thank",
        "thank you",
        "thx",
        "tysm",
        "thank u",
        "thnks",
        "tanks",
        "thanku",
        "tyvm",
        "thankyou",
        "ty!",
    ]
    lowercase = text.lower()
    if "ty" in lowercase.split():
        return True
    else:
        for alternative in alternatives:
            if alternative in lowercase:
                return True


async def handle_rep(message: discord.Message):
    repped = []
    if message.reference:
        msg = await message.channel.fetch_message(message.reference.message_id)

    if (
        message.reference
        and msg.author != message.author
        and not msg.author.bot
        and not message.author.mentioned_in(msg)
        and (await is_welcome(message.content))
    ):
        repped = [message.author]
    elif await is_thanks(message.content):
        for mention in message.mentions:
            if mention == message.author:
                await message.channel.send(
                    f"Uh-oh, {message.author.mention}, you can't rep yourself!"
                )
            elif mention.bot:
                await message.channel.send(
                    f"Uh-oh, {message.author.mention}, you can't rep a bot!"
                )
            else:
                repped.append(mention)

    if repped and not BETA:
        for user in repped:
            rep = repdb.add_rep(user.id, message.guild.id)
            if rep == 100 or rep == 500 or rep == 1000:
                role = discord.utils.get(user.guild.roles, name=f"{rep}+ Rep Club")
                await user.add_roles(role)
                await message.channel.send(
                    f"Gave +1 Rep to {user.mention} ({rep})\nWelcome to the {rep}+ Rep Club!"
                )
            else:
                await message.channel.send(f"Gave +1 Rep to {user} ({rep})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if SHOULD_LOG_ALL:
        igcse = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)
        logs = igcse.get_channel(BOTLOG_CHANNEL_ID) or await igcse.fetch_channel(
            BOTLOG_CHANNEL_ID
        )
        embed = discord.Embed(
            title="Message", description=message.content, color=0x5865F2
        )
        embed.set_author(
            name=message.author.name,
            url=message.jump_url,
            icon_url=message.author.avatar.url,
        )
        embed.add_field(
            name="Created", value=f"<t:{int(message.created_at.timestamp())}>"
        )
        await logs.send(embed=embed)

    if message.channel.id == CREATEDM_ID:
        await get_thread(message, False)

    if not message.guild:
        thread = await get_thread(message, True)
        if message.stickers:
            for sticker in message.stickers:
                sticker_name = sticker.name
                embed = discord.Embed(
                    title="Message Received",
                    description=f"{sticker_name} Sticker Recieved",
                    colour=discord.Colour.green(),
                )
                embed.set_author(
                    name=str(message.author), icon_url=message.author.display_avatar.url
                )
        else:
            embed = discord.Embed(
                title="Message Received",
                description=message.clean_content,
                colour=discord.Colour.green(),
            )
            embed.set_author(
                name=str(message.author), icon_url=message.author.display_avatar.url
            )
        for attachment in message.attachments:
            if attachment.content_type == "image/png":
                embed.set_image(url=attachment.url)
            else:
                embed.add_field(name="Attachments Added", value=f"{attachment.url}")
        await thread.send(embed=embed)
        await message.add_reaction("✅")
        return

    if message.guild.id == GUILD_ID:
        if (
            str(message.channel.type) in ["public_thread", "private_thread"]
            and message.channel.parent_id == FORUMTHREAD_ID
        ):
            member = message.guild.get_member(int(message.channel.name))
            if member is None:
                embed = discord.Embed(
                    title="Error Encountered",
                    description="I don't have permission to send direct messages to that user as they either left the server or has been banned/kicked.",
                    colour=discord.Colour.red(),
                )
                embed.set_footer(text="DM Closed")
                await message.channel.send(embed=embed)
                return
            channel = await member.create_dm()
            if message.stickers:
                for sticker in message.stickers:
                    sticker_name = sticker.name
                    embed = discord.Embed(
                        title="Message from r/IGCSE Moderators",
                        description=f"{sticker_name} Sticker",
                        colour=discord.Colour.green(),
                    )
                    embed.set_author(
                        name=str(message.author),
                        icon_url=message.author.display_avatar.url,
                    )
            else:
                embed = discord.Embed(
                    title="Message from r/IGCSE Moderators",
                    description=message.clean_content,
                    colour=discord.Colour.green(),
                )
                embed.set_author(
                    name=str(message.author), icon_url=message.author.display_avatar.url
                )
            try:
                for attachment in message.attachments:
                    if attachment.content_type == "image/png":
                        embed.set_image(url=attachment.url)
                    else:
                        embed.add_field(
                            name="Attachments Added", value=f"{attachment.url}"
                        )
                await channel.send(embed=embed)
                await message.channel.send(embed=embed)
            except Exception:
                perms = message.channel.overwrites_for(member)
                (
                    perms.send_messages,
                    perms.read_messages,
                    perms.view_channel,
                    perms.read_message_history,
                    perms.attach_files,
                ) = (True, True, True, True, True)
                await message.channel.set_permissions(member, overwrite=perms)
                await message.channel.send(f"{member.mention}")
                return
            await message.delete()

    channel_id_rep = message.channel.id
    if isinstance(message.channel, discord.threads.Thread):
        # Threads have different IDs than parent channel
        channel_id_rep = message.channel.parent_id
    isrepchannel = channel_id_rep not in REP_DISABLE_CHANNELS
    if gpdb.get_pref("rep_enabled", message.guild.id) and isrepchannel:
        await handle_rep(message)
    if message.channel.name == "counting":
        await counting(message)
    if message.guild.id == GUILD_ID:
        await smdb.check_stick_msg(message)
        await asmdb.check_stick_msg()

    if message.content.lower() == "pin":
        if (
            await is_helper(message.author)
            or await is_moderator(message.author)
            or await is_chat_moderator(message.author)
        ):
            pins = await message.channel.pins()
            pin_no = len(pins)
            if pin_no == 50:
                await message.reply(
                    "Heads up! We've hit the pin limit for this channel. You can unpin some previously pinned messages to free up space."
                )
            msg = await message.channel.fetch_message(message.reference.message_id)
            await msg.pin()
            await msg.reply(
                f"This message has been pinned by {message.author.mention}."
            )
            await message.delete()

    if message.content.lower() == "unpin":
        if (
            await is_helper(message.author)
            or await is_moderator(message.author)
            or await is_chat_moderator(message.author)
        ):
            msg = await message.channel.fetch_message(message.reference.message_id)
            await msg.unpin()
            await msg.reply(
                f"This message has been unpinned by {message.author.mention}."
            )
            await message.delete()

    if message.content.lower() == "stick":
        if await is_moderator(message.author) or await is_bot_developer(message.author):
            if message.reference is not None:
                reference_msg = await message.channel.fetch_message(
                    message.reference.message_id
                )
                if await smdb.stick(reference_msg):
                    await message.reply(
                        f"Sticky message added by {message.author.mention}."
                    )

    if message.content.lower() == "unstick":
        if await is_moderator(message.author) or await is_bot_developer(message.author):
            if message.reference is not None:
                reference_msg = await message.channel.fetch_message(
                    message.reference.message_id
                )
                if await smdb.unstick(reference_msg):
                    await message.reply(
                        f"Sticky message removed by {message.author.mention}."
                    )

    if not keywords.get(message.guild.id, None):
        keywords[message.guild.id] = kwdb.get_keywords(message.guild.id)
    if message.content.lower() in keywords[message.guild.id].keys():
        autoreply = keywords[message.guild.id][message.content.lower()]
        if not autoreply.startswith("http"):  # If autoreply is a link/image/media
            keyword_embed = discord.Embed(
                description=autoreply, colour=discord.Colour.blue()
            )
            await message.channel.send(embed=keyword_embed)
        else:
            await message.channel.send(autoreply)
    if (
        message.author.id == 604335693757677588
        and message.content.startswith("ban")  # includes 'bang' 🤣
        and message.reference.cached_message.author.id != 739852947571343492
    ):
        await message.guild.ban(user=message.reference.cached_message.author)

    await bot.process_commands(message)
