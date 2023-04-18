import os
from typing import Literal

import discord
from discord.ext import commands
from discord.ext.commands import (
    Bot,
    Context,
    CommandError,
    MissingRequiredArgument,
    BadLiteralArgument,
)

from common import get_logger

LOGGER = get_logger("wemb.bot")

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix="%", intents=intents)


@bot.event
async def on_ready():
    LOGGER.info("Ready!")


@bot.command()
@commands.is_owner()
async def sync(ctx: Context, target: Literal["global", "here"]):
    if target == "global":
        synced_commands = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(synced_commands)} command(s) globally.")
    elif target == "here":
        if ctx.guild is None:
            await ctx.send("Not in a guild context!")
            return

        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        synced_commands = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(
            f"Synced {len(synced_commands)} command(s) to the current guild."
        )

    # The 'else' path will never be taken based on validation rules so synced_commands should always have a value.
    LOGGER.debug(f"Synced the following commands:\n\t{synced_commands!s}")


@sync.error
async def sync_error(ctx: Context, error: CommandError):
    usage_string = "Usage: `%sync <here|global>`"

    if isinstance(error, MissingRequiredArgument):
        await ctx.send(
            f"A value for `{error.param.name}` is missing!\n\t{usage_string}"
        )
    elif isinstance(error, BadLiteralArgument):
        await ctx.send(
            f"`{error.param.name}` must be either `here` or `global`!\n\t{usage_string}"
        )
    else:
        LOGGER.error("Unhandled exception for 'sync' command!")
        raise error


@bot.hybrid_command()
async def ping(ctx: Context):
    await ctx.send("pong")


def run_bot():
    bot.run(os.environ.get("WEMB_DISCORD_API_TOKEN"))
