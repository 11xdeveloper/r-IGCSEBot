from bot import discord

async def is_banned(user, guild):
    try:
        await guild.fetch_ban(user)
        return True
    except discord.NotFound:
        return False