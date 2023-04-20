import asyncio
from argparse import Namespace
from typing import Literal, List, Optional

import discord
from discord import Interaction, app_commands, InteractionResponse
from discord.app_commands import Transformer, Range, Transform
from discord.ext import commands
from discord.ext.commands import (
    Bot,
    Context,
    CommandError,
    MissingRequiredArgument,
    BadLiteralArgument,
    GroupCog,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from common import get_engine, get_logger
from models import SubmissionType, SubmissionCriterion, Keyword
from monitor import run_monitor

PROGRAM_ARGS: Optional[Namespace] = None
MONITOR_TASK: Optional[asyncio.Task] = None
LOGGER = get_logger("wemb.bot")

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix="%", intents=intents)


@bot.event
async def on_ready():
    global MONITOR_TASK

    LOGGER.debug("Adding cogs...")
    await bot.add_cog(Searches())

    LOGGER.info("Starting Monitor...")
    MONITOR_TASK = asyncio.create_task(
        run_monitor(PROGRAM_ARGS),
        name="monitor",
    )

    LOGGER.info("Done!")


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

    # noinspection PyUnboundLocalVariable
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


@bot.hybrid_command(description="Pings the bot to check if it's alive")
async def ping(ctx: Context):
    await ctx.send("pong")


class Searches(
    GroupCog,
    name="searches",
    description="Manages submission search criteria that this bot listens for",
):
    class KeywordListTransformer(Transformer):
        async def transform(
            self, interaction: Interaction, value: str, /
        ) -> List[Keyword]:
            return [Keyword(content=keyword) for keyword in value.split()]

    @app_commands.command(name="add")
    @app_commands.describe(
        submission_type="The 'type' of post you are looking for (Want to buy / Want to sell)",
        keywords="Space-separated list of keywords to search for. Case insensitive.",
        all_required="Whether all keywords are required to match (true), or only just one (false). Default is true",
        min_transactions="The minimum transaction count of the posting user, shown in their flair. Default is 5",
    )
    async def add(
        self,
        interaction: Interaction[Bot],
        submission_type: SubmissionType,
        keywords: Transform[List[Keyword], KeywordListTransformer],
        all_required: bool = True,
        min_transactions: Range[int, 1] = 5,
    ):
        """Add a search for a particular item on the subreddit"""
        # noinspection PyTypeChecker
        response: InteractionResponse[Bot] = interaction.response

        await response.send_message("Creating...")

        with Session(get_engine()) as session:
            criterion = SubmissionCriterion(
                submission_type=submission_type,
                keywords=keywords,
                all_required=all_required,
                min_transactions=min_transactions,
            )
            session.add(criterion)
            session.commit()

            await interaction.edit_original_response(content=f"Created!\n{criterion!r}")

    @app_commands.command(name="list")
    async def list(self, interaction: Interaction[Bot]):
        """Lists all current search criteria"""
        # noinspection PyTypeChecker
        response: InteractionResponse[Bot] = interaction.response

        await response.send_message("Please wait...")

        with Session(get_engine()) as session:
            await interaction.edit_original_response(
                content="Search criteria:\n"
                + "\t\n".join(
                    (str(c) for c in session.scalars(select(SubmissionCriterion)))
                )
            )

    @app_commands.command(name="delete")
    @app_commands.describe(
        search_id="The id (primary key) of the search criterion you want to remove."
    )
    async def delete(self, interaction: Interaction[Bot], search_id: Range[int, 0]):
        """Remove a specified search criteria by ID"""
        # noinspection PyTypeChecker
        response: InteractionResponse[Bot] = interaction.response

        await response.send_message("Please wait...")

        with Session(get_engine()) as session:
            criterion: SubmissionCriterion = session.scalar(
                select(SubmissionCriterion).where(SubmissionCriterion.id == search_id)
            )

            if criterion is None:
                await interaction.edit_original_response(
                    content=f"Search criteria not found for id {search_id}!"
                )
                return

            session.delete(criterion)
            session.commit()

        await interaction.edit_original_response(content="Successfully deleted!")


def run_bot(args: Namespace):
    global PROGRAM_ARGS

    # We will need access to these args when instantiating the PRAW instance
    PROGRAM_ARGS = args
    bot.run(args.discord_api_token)
