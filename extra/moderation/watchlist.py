# import.standard
import os
from datetime import datetime
from typing import List, Optional, Union

# import.thirdparty
import discord
from discord.ext import commands

# import.local
from extra import utils
from mysqldb import DatabaseCore

# variables.role
allowed_roles = [int(os.getenv('OWNER_ROLE_ID', 123)), int(os.getenv('ADMIN_ROLE_ID', 123)), int(os.getenv('MOD_ROLE_ID', 123))]

# variables.textchannel
mod_log_id = int(os.getenv('MOD_LOG_CHANNEL_ID', 123))

class ModerationWatchlistTable(commands.Cog):

    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.db = DatabaseCore()

    @commands.command(aliases=['wl'])
    @utils.is_allowed(allowed_roles, throw_exc=True)
    async def watchlist(self, ctx, *, message: Optional[str] = None) -> None:
        """ Puts an entry into one or more members watchlist. If the user already has an entry in their watchlist, another entry will be added.

        :param member: The member(s) to put an entry into their watchlist.
        :param note: The note to be added with the entry into the member(s) watchlist. """

        await ctx.message.delete()

        members, note = await utils.greedy_member_reason(ctx, message)

        author = ctx.author

        if not members:
            await ctx.send(f"**Please, inform a member to put in the watchlist, {author.mention}!**", delete_after=3)
        else:
            if note is not None and len(note) > 960:
                return await ctx.send(f"**Please, inform a note that is lower than or equal to 960 characters, {author.mention}!**", delete_after=3)

            for member in members:
                # General embed
                infr = "watchlist"
                whitelist_desc = f'**Note:** {note}'
                general_embed = discord.Embed(description=whitelist_desc, colour=author.color)
                general_embed.set_author(name=f'{member} has been watchlisted', icon_url=member.display_avatar)
                await ctx.send(embed=general_embed)
                # Moderation log embed
                moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
                current_ts = await utils.get_timestamp()
                infr_date = datetime.fromtimestamp(current_ts).strftime('%Y/%m/%d at %H:%M')
                perpetrator = ctx.author.name if ctx.author else "Unknown"
                embed = discord.Embed(title='__**Watchlist**__', colour=discord.Colour.lighter_gray(),
                                timestamp=ctx.message.created_at)
                embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                                inline=False)
                embed.add_field(name='Note:', value=f"> -# **{infr_date}**\n> -# by {perpetrator}\n> {note}")
                embed.set_author(name=member)
                embed.set_thumbnail(url=member.display_avatar)
                embed.set_footer(text=f"Watchlisted by {author}", icon_url=author.display_avatar)
                await moderation_log.send(embed=embed)
                # Inserts a watchlist into the database
                await self.insert_user_infraction(user_id=member.id, infr_type=infr, reason=note, timestamp=current_ts, perpetrator=ctx.author.id)


    # Retrieves all watchlist from the database. Could be useful in future.
    async def get_user_wl_entries(self, user_id: int) -> List[List[Union[str, int]]]:
        """ Gets all watchlists from a user. """

        return await self.db.execute_query(
            "SELECT * FROM UserInfractions WHERE user_id = %s AND infraction_type = %s", (user_id, "watchlist"), fetch="all"
            )
