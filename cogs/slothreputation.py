# import.standard
import os
from typing import List, Optional, Union

# import.thirdparty
import discord
from discord import Option, slash_command
from discord.ext import commands

# import.local
from extra import utils
from extra.slothclasses.player import Player
from extra.view import ExchangeActivityView
from mysqldb import DatabaseCore
from extra.slothclasses.mastersloth import classes
from extra.currency.membersscore import MembersScoreTable
from extra.misc.slothactions import SlothActionsTable

# variables.id
guild_ids = [int(os.getenv('SERVER_ID', 123))]

# variables.textchannel
commands_channel_id = int(os.getenv('BOTS_AND_COMMANDS_CHANNEL_ID', 123))

currency_cogs: List[commands.Cog] = [
    MembersScoreTable, SlothActionsTable
]

class SlothReputation(*currency_cogs):
    """ Reputation commands. """

    def __init__(self, client):
        self.client = client
        self.db = DatabaseCore()

    @commands.Cog.listener()
    async def on_ready(self):
        print("[.cogs] SlothReputation cog is ready!")

    # In-game commands
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return

        if message.author.bot:
            return
        elif not await self.check_members_score_table_exists():
            return

        currnet_ts = await utils.get_timestamp()
        await self.update_data(message.author, currnet_ts)

    async def update_data(self, user, current_ts):
        the_member = await self.get_specific_user(user.id)
        if the_member:
            if current_ts - the_member[0][3] >= 3 or the_member[0][1] == 0:
                await self.update_user_xp_time(user.id, current_ts)
                await self.update_user_xp(user.id, 5)
                return await self.level_up(user)
        # else:
        #     return await self.insert_user(user.id, 5, 1, current_ts, 0, time_xp - 36001)

    async def level_up(self, user) -> discord.Message:
        """ Checks whether the user can level up.
        :param user: The user to check. """

        the_user = await self.get_specific_user(user.id)
        lvl_end = int(the_user[0][1] ** (1 / 5))
        if the_user[0][2] < lvl_end:
            await self.client.get_cog('SlothCurrency').update_user_money(user.id, (the_user[0][2] + 1) * 5)
            await self.update_user_lvl(user.id)
            await self.update_user_score_points(user.id, 100)
            channel = discord.utils.get(user.guild.channels, id=commands_channel_id)
            return await channel.send(f"**{user.mention} has leveled up to lvl {the_user[0][2] + 1}! <:zslothrich:701157794686042183> Here's {(the_user[0][2] + 1) * 5}łł! <:zslothrich:701157794686042183>**")


    async def get_progress_bar(self, lvl: int, xp: int, goal_xp, length_progress_bar: int = 17) -> str:
        """ Gets a string/emoji progress bar.
        :param lvl: The user level.
        :param xp: The current XP of the user.
        :param goal_xp: The XP they are trying to achieve.
        :param length_progress_bar: The amount of blocks in the bar. Default=20 """

        percentage = int((xp / goal_xp) * 100)
        boxes = int((percentage * length_progress_bar) / 100)
        progress_bar = f"> 📊 **Level**: {lvl} ({xp}xp / {goal_xp}xp) {percentage}%\n> {':blue_square:' * boxes}{':white_large_square:' * (length_progress_bar - boxes)}"
        return progress_bar

    @commands.command(name="info", aliases=['status', 'exchange', 'level', 'lvl', 'exp', 'xp'])
    @Player.poisoned()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _info_command(self, ctx, member: Optional[Union[discord.Member, discord.User]] = None) -> None:
        """ Shows the user's level and experience points.
        :param member: The member to show the info. [Optional][Default=You] """

        await self._info(ctx, member)

    @slash_command(name="info", guild_ids=guild_ids)
    @Player.poisoned()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _info_slash(self, ctx, 
        member: Option(discord.Member, description="The member to show the info; [Default=Yours]", required=False)) -> None:
        """ Shows the user's level and experience points. """

        await ctx.defer()
        await self._info(ctx, member)

    async def _info(self, ctx, member: Union[discord.Member, discord.User] = None) -> None:
        """ Shows the user's level and experience points.
        :param ctx: The context of the command.
        :param member: The member for whom to show the info. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        if not await self.check_members_score_table_exists():
            return await answer("**This command may be on maintenance!**")

        author = ctx.author

        if not member:
            member = author

        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=5, label="Create Account", emoji="🦥", url="https://languagesloth.com/profile/update"))

        # Gets users ranking info, such as level and experience points
        user = await self.get_specific_user(member.id)
        if not user:
            if author.id == member.id:
                return await answer( 
                    embed=discord.Embed(description=f"**{member.mention}, you don't have an account yet. Click [here](https://languagesloth.com/profile/update) to create one, or in the button below!**"),
                    view=view)
            else:
                return await answer(f"**{member} doesn't have an account yet!**")

        # Gets user's currency info, such as money balance, class participations, sloth class, etc.
        SlothCurrency = self.client.get_cog('SlothCurrency')

        ucur = await SlothCurrency.get_user_currency(member.id)
        sloth_profile = await self.client.get_cog('SlothClass').get_sloth_profile(member.id)
        if not ucur or not sloth_profile:
            if author.id == member.id:
                return await answer( 
                    embed=discord.Embed(description=f"**{member.mention}, you don't have an account yet. Click [here](https://languagesloth.com/profile/update) to create one, or in the button below!**"),
                    view=view)
            else:
                return await answer(f"**{member} doesn't have an account yet!**")

        SlothClass = self.client.get_cog('SlothClass')
        effects = await SlothClass.get_user_effects(member=member)

        if 'hacked' in effects:
            await SlothCurrency.send_hacked_image(answer, author, member)
            if author.id != member.id:
                 await SlothClass.check_virus(ctx=ctx, target=member)
            return

        all_users = await self.get_all_users_by_score_points()
        position = [[i+1, u[4]] for i, u in enumerate(all_users) if u[0] == member.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        # Gets user Server Activity info, such as messages sent and time in voice channels
        user_info = await SlothCurrency.get_user_activity_info(member.id)
        if not user_info and member.id == author.id:
            return await answer(f"**For some reason you are not in the system, {author.mention}! Try again**")

        elif not user_info and not member.id == author.id:
            return await answer("**Member not found in the system!**")
    
        current_time = await utils.get_time_now()
        embed = discord.Embed(title="__All Information__", colour=member.color, timestamp=current_time)
        xp = user[0][1]
        goal_xp = ((user[0][2]+1)**5)
        lvl = user[0][2]
        
        # All time activity
        all_msgs = await self.get_sloth_actions(member.id, "message-exchange")
        all_msgs = sum([int(am[4]) for am in all_msgs]) + int(user_info[0][1])

        all_time = await self.get_sloth_actions(member.id, "time-exchange")
        all_time = sum([int(at[4]) for at in all_time]) + user_info[0][2]

        a_m, _ = divmod(all_time, 60)
        a_h, a_m = divmod(a_m, 60)

        # Exchangeable activity
        m, _ = divmod(user_info[0][2], 60)
        h, m = divmod(m, 60)
        

        embed.add_field(name="__**`General`**__", value=f"""
        > 🍃 **Balance**: {ucur[0][1]}łł & {ucur[0][7]}gł
        > 📈 **All Time Activity**: {a_h:d} hours, {a_m:02d} minutes and {all_msgs} messages.
        > 💰 **Exchangeable Activity**: {h:d} hours, {m:02d} minutes and {user_info[0][1]} messages.
        > 🏆 **Reputation**: {position[1]} pts | #{position[0]}
        """, inline=True)

        embed.add_field(name="__**`Classes`**__", value=f"""
        > 🧑‍🎓 **Participated in:** {ucur[0][3]}
        > 🌟 **Rewarded in**: {ucur[0][4]}
        > 🧑‍🏫 **Hosted**: {ucur[0][5]}
        """, inline=True)

        progress_bar = await self.get_progress_bar(lvl=lvl, xp=xp, goal_xp=goal_xp)
        embed.add_field(name="__**`Progress Bar`:**__", value=progress_bar, inline=False)

        emoji = user_class.emoji if (user_class := classes.get(sloth_profile[1].lower())) else ''
        embed.add_field(name="__**`Sloth`**__", value=f"""
        > 🕵️ **Sloth Class:** {sloth_profile[1]} {emoji}
        > 🧮 **Skills Used:** {sloth_profile[2]}
        > 🔪 **Knife Sharpness Stack:** {ucur[0][5]}
        > 🍯 **Has Potion:** {True if sloth_profile[5] else False}
        > 💍 **Rings:** {sloth_profile[7]}/2
        """, inline=True)

        embed.add_field(name="__**`Buffs & Debuffs`**__", value=f"""
        > 🛡️ **Protected:** {await SlothClass.has_effect(effects, 'protected')}
        > 😵 **Knocked Out:** {await SlothClass.has_effect(effects, 'knocked_out')}
        > 🔌 **Wired:** {await SlothClass.has_effect(effects, 'wired')}
        > 🐸 **Frogged:** {await SlothClass.has_effect(effects, 'frogged')}
        > 🧤 **Sabotaged:** {await SlothClass.has_effect(effects, 'sabotaged')}
        > 🤐 **Kidnapped:** {True if await SlothClass.has_effect(effects, 'kidnapped') else False}
        """, inline=True)

        # Gets tribe information for the given user
        tribe_member = await SlothClass.get_tribe_member(user_id=member.id)
        if tribe_member:
            user_tribe = await SlothClass.get_tribe_info_by_name(name=sloth_profile[3])
            tribe_owner = tribe_member[0] == tribe_member[2]
            embed.add_field(
                name="🏕️ __**`Tribe`**__", 
                value=f"[{user_tribe['name']}]({user_tribe['link']}) ({user_tribe['two_emojis']}){' 👑' if tribe_owner else ''}", 
                inline=False)
        else:
            embed.add_field(name="🏕️ __**`Tribe`**__", value="None", inline=False)

        if user_baby := await SlothClass.get_user_baby(member.id):
            baby_emoji: str = ''
            if user_baby[3].lower() != 'embryo':
                baby_emoji = classes.get(user_baby[3].lower()).emoji
            else:
                baby_emoji = '🥚'

            embed.add_field(
                name=f"{baby_emoji} __**`Baby`**__", 
                value=f"**{user_baby[2]}** (<t:{user_baby[8]}:R>).", 
                inline=True)

        if user_pet := await SlothClass.get_user_pet(member.id):
            embed.add_field(
                name="🐸 __**`Pet`**__", 
                value=f"**{user_pet[1]}** (<t:{user_pet[7]}:R>). **{user_pet[2]}**", 
                inline=True)

        if marriages := await SlothClass.get_user_marriages(member.id):
            text = f"**Married to:**\n"
            for marriage in marriages:
                text += f"> <@{marriage['partner']}> (<t:{marriage['timestamp']}:R>).{' 🌛' if marriage['honeymoon'] else ''}\n"
            embed.add_field(name="💍 __**`Marriages`**__", value=text, inline=False)

            divorces = await self.get_sloth_actions(member.id, "divorce", check_target=True)
            embed.add_field(name="💔 __**`Divorces`**__", value=f"{len(divorces)} divorces.", inline=True)

        embed.set_thumbnail(url=member.display_avatar)
        embed.set_author(name=member, icon_url=member.display_avatar, url=member.display_avatar)

        user: discord.User = await self.client.fetch_user(member.id)
        if banner := user.banner:
            embed.set_image(url=banner.url)
        embed.set_footer(text=ctx.guild, icon_url=ctx.guild.icon.url)

        if member.id != member.id:
            return await answer(embed=embed)
        else:
            view = ExchangeActivityView(self.client, user_info[0])
            if 'sabotaged' in effects:
                view.children[0].disabled = True

            return await answer(embed=embed, view=view)

    @slash_command(name="leaderboard", guild_ids=guild_ids)
    @Player.poisoned()
    async def _leaderboard(self, ctx, 
        info_for: Option(str, description="The leaderboard to show the information for.", choices=[
            'Reputation', 'Level', 'Leaves', 'Time', 'Items', 'Memory', 'Tribe Leaves', 'Blackjacks', 'Coinflips'
        ]
    )) -> None:
        """ Shows the leaderboard. """

        if info_for == 'Reputation':
            await self.score(ctx)
        elif info_for == 'Level':
            await self.level_score(ctx)
        elif info_for == 'Leaves':
            await self.leaf_score(ctx)
        elif info_for == 'Time':
            await self.time_score(ctx)
        elif info_for == 'Items':
            await self.items_score(ctx)
        elif info_for == 'Memory':
            await self.memory_score(ctx)
        elif info_for == 'Tribe Leaves':
            await self.tribe_leaf_score(ctx)
        elif info_for == 'Blackjacks':
            await self.blackjack_score(ctx)
        elif info_for == 'Coinflips':
            await self.coinflips_score(ctx)

    @commands.command(aliases=['leaderboard', 'lb', 'scoreboard'])
    @Player.poisoned()
    async def score(self, ctx):
        """ Shows the top ten members in the reputation leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        if not await self.check_members_score_table_exists():
            return await answer("**This command may be on maintenance!**")

        top_ten_users = await self.get_top_ten_users()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="__The Language Sloth's Leaderboard__", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)
        all_users = await self.get_all_users_by_score_points()
        position = [[i+1, u[4]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your score: {position[1]} | #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", value=f"__**Score:**__ `{sm[4]}`",
                                  inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['level_board', 'levelboard', 'levels'])
    @Player.poisoned()
    async def level_score(self, ctx):
        """ Shows the top ten members in the level leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        top_ten_users = await self.get_top_ten_xp_users()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="__The Language Sloth's Level Ranking Leaderboard__", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)
        all_users = await self.get_all_users_by_xp()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your XP: {position[1]} | #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", value=f"__**Level:**__ `{sm[2]}` | __**XP:**__ `{sm[1]}`",
                                  inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['leaf_board', 'leafboard', 'leaves', 'leaves_leaderboard', 'leavesleaderboard', 'll'])
    @Player.poisoned()
    async def leaf_score(self, ctx):
        """ Shows the top ten members in the leaves leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        SlothCurrency = self.client.get_cog('SlothCurrency')

        top_ten_users = await SlothCurrency.get_top_ten_leaves_users()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="🍃 __The Language Sloth's Leaf Ranking Leaderboard__ 🍃", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)

        all_users = await SlothCurrency.get_all_leaves_users()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your leaves: {position[1]} 🍃| #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", value=f"__**Leaves:**__ `{sm[1]}` 🍃",
                                  inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['tribe_leaf_board', 'tribeleafboard', 'tribeleaves', 'tribe_leaves_leaderboard', 'tribeleavesleaderboard', 'tll'])
    @Player.poisoned()
    async def tribe_leaf_score(self, ctx):
        """ Shows the top ten tribes with most leaves in the leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        SlothClass = self.client.get_cog('SlothClass')

        top_ten_tribes = await SlothClass.get_top_ten_tribe_leaves()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="🍃 __The Language Sloth's Tribe Leaf Ranking Leaderboard__ 🍃", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, tribe in enumerate(top_ten_tribes):
            leaderboard.add_field(name=f"[{i + 1}]# - __**{tribe[0]}**__", value=f"__**Leaves:**__ `{tribe[1]}` 🍃",
                                  inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['time_board', 'timeboard', 'time_leaderboard', 'timeleaderboard', 'tl'])
    @Player.poisoned()
    async def time_score(self, ctx):
        """ Shows the top ten members in the time leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        SlothCurrency = self.client.get_cog('SlothCurrency')

        top_ten_users = await SlothCurrency.get_top_ten_time_users()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="⏰ __The Language Sloth's Time Ranking Leaderboard__ ⏰", color=discord.Color.dark_green(),
                                    timestamp=current_time)

        all_users = await SlothCurrency.get_all_time_users()
        position = [[i+1, u[2]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        m, s = divmod(position[1], 60)
        h, m = divmod(m, 60)

        leaderboard.set_footer(text=f"Your time: {h:d}h, {m:02d}m ⏰| #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            m, s = divmod(sm[2], 60)
            h, m = divmod(m, 60)
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", value=f"__**Time:**__ `{h:d}h, {m:02d}m.` ⏰",
                                  inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['items_board', 'itemsboard', 'items_leaderboard', 'itemsleaderboard', 'il'])
    @Player.poisoned()
    async def items_score(self, ctx):
        """ Shows the top ten members in the items leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        SlothCurrency = self.client.get_cog('SlothCurrency')

        top_ten_users = await SlothCurrency.get_top_ten_item_counter_users()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="🐮 __The Language Sloth's Items Ranking Leaderboard__ 🐮", color=discord.Color.dark_green(),
                                    timestamp=current_time)

        all_users = await SlothCurrency.get_item_counter_users()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your time: {position[1]} items | #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", value=f"__**Items:**__ `{sm[1]}` items 🐮", inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['memory_board', 'memoryboard', 'memories'])
    @Player.poisoned()
    async def memory_score(self, ctx):
        """ Shows the top ten members in the memory leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        Games = self.client.get_cog("Games")

        top_ten_users = await Games.get_top_ten_memory_users()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="__The Language Sloth's Memory Ranking Leaderboard__", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)
        all_users = await Games.get_all_memory_users_by_level()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your level: {position[1]} | #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", 
                value=f"__**Level:**__ `{sm[1]}` (<t:{sm[2]}:R>)",
                                  inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=[
        'blackjack_board', 'blackjackboard', 'bjscore', 'bjboard', 
        'whitejack_board', 'whitejackboard', 'whitejack_score', 'wjscore', 'wjboard'
    ]
    )
    @Player.poisoned()
    async def blackjack_score(self, ctx):
        """ Shows the top ten members in the blackjack leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        Games = self.client.get_cog("Games")
        top_ten_users = await Games.get_top_ten_blackjack_members_by_wins()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="__The Language Sloth's Blackjack Ranking Leaderboard__", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)
        all_users = await Games.get_all_blackjack_members_by_wins()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your wins: {position[1]} | #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]#", value=f"**__{member}__ • Wins:** `{sm[1]}`", inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command(aliases=['coinflips_board', 'coinflipsboard', 'coinflip_score', 'coinflip_board', 'coinflipboard', 'cfscore', 'cfboard'])
    @Player.poisoned()
    async def coinflips_score(self, ctx):
        """ Shows the top ten members in the coinflips leaderboard. """

        answer: discord.PartialMessageable = None
        if isinstance(ctx, commands.Context):
            answer = ctx.send
        else:
            answer = ctx.respond

        Games = self.client.get_cog("Games")
        top_ten_users = await Games.get_top_ten_coinflip_members_by_wins()
        current_time = await utils.get_time_now()
        leaderboard = discord.Embed(title="__The Language Sloth's Coinflips Ranking Leaderboard__", colour=discord.Colour.dark_green(),
                                    timestamp=current_time)
        all_users = await Games.get_all_coinflip_members_by_wins()
        position = [[i+1, u[1]] for i, u in enumerate(all_users) if u[0] == ctx.author.id]
        position = [it for subpos in position for it in subpos] if position else ['??', 0]

        leaderboard.set_footer(text=f"Your wins: {position[1]} | #{position[0]}", icon_url=ctx.author.display_avatar)
        leaderboard.set_thumbnail(url=ctx.guild.icon.url)

        # Embeds each one of the top ten users.
        for i, sm in enumerate(top_ten_users):
            member = discord.utils.get(ctx.guild.members, id=sm[0])
            leaderboard.add_field(name=f"[{i + 1}]# - __**{member}**__", value=f"**Wins:** `{sm[1]}` • **Last time played:** <t:{sm[3]}:R>)", inline=False)
            if i + 1 == 10:
                break
        return await answer(embed=leaderboard)

    @commands.command()
    @Player.poisoned()
    async def rep(self, ctx, member: discord.Member = None):
        """ Gives someone reputation points.
        :param member: The member to give the reputation.

        Ps: The repped person gets 5łł and 100 reputation points. """

        author: discord.Member = ctx.author

        if not member:
            await ctx.message.delete()
            return await ctx.send(f"**Inform a member to rep to!**", delete_after=3)

        if member.id == author.id:
            await ctx.message.delete()
            return await ctx.send(f"**You cannot rep yourself!**", delete_after=3)

        user = await self.get_specific_user(author.id)
        if not user:
            return await self.rep(ctx)

        await ctx.message.delete()

        target_user = await self.get_specific_user(member.id)
        if not target_user:
            if author.id == member.id:

                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=5, label="Create Account", emoji="🦥", url="https://languagesloth.com/profile/update"))
                return await ctx.send( 
                    embed=discord.Embed(description=f"**{member.mention}, you don't have an account yet. Click [here](https://languagesloth.com/profile/update) to create one, or in the button below!**"),
                    view=view)
            else:
                return await ctx.send("**This member is not on the leaderboard yet!**", delete_after=3)

        SlothClass = self.client.get_cog('SlothClass')

        perpetrator_fx = await SlothClass.get_user_effects(author)
        if 'sabotaged' in perpetrator_fx:
            return await ctx.send(f"**You can't rep anyone because you have been sabotaged, {author.mention}!**")

        target_fx = await SlothClass.get_user_effects(member)
        if 'sabotaged' in target_fx:
            return await ctx.send(f"**You can't rep {member.mention} because they have been sabotaged, {author.mention}!**")

        current_ts = await utils.get_timestamp()
        sub_time = current_ts - user[0][5]
        cooldown = 36000
        if int(sub_time) < int(cooldown):
            m, s = divmod(int(cooldown) - int(sub_time), 60)
            h, m = divmod(m, 60)
            if h > 0:
                return await ctx.send(f"**Rep again in {h:d} hours, {m:02d} minutes and {s:02d} seconds!**",
                                      delete_after=10)
            elif m > 0:
                return await ctx.send(f"**Rep again in {m:02d} minutes and {s:02d} seconds!**", delete_after=10)
            elif s > 0:
                return await ctx.send(f"**Rep again in {s:02d} seconds!**", delete_after=10)

        rep_points: int = 100
        if await SlothClass.get_user_pet(author.id): rep_points += 100
        if await SlothClass.get_user_baby(author.id): rep_points += 100

        await self.update_user_score_points(author.id, rep_points)
        await self.update_user_score_points(member.id, rep_points)
        await self.update_user_rep_time(author.id, current_ts)
        await self.client.get_cog('SlothCurrency').update_user_money(member.id, 5)
        await ctx.send(
            f"**{author.mention} repped {member.mention}! 🍃The repped person got 5łł🍃**")

        user_quest = await SlothClass.get_skill_action_by_user_id_and_skill_type(user_id=author.id, skill_type="quest")
        if user_quest and user_quest[9] == 0:
            await SlothClass.update_sloth_skill_target_id(author.id, member.id, current_ts, 'quest')
            return await SlothClass.complete_quest(author.id, 2)

        target_quest = await SlothClass.get_skill_action_by_user_id_and_skill_type(user_id=member.id, skill_type="quest")
        if target_quest and target_quest[3] == author.id:
            # Tries to complete a Quest, if possible
            await SlothClass.complete_quest(member.id, 2)

    @commands.command(aliases=["actions", "divorces", "transfers", "baby_deaths", "pet_deaths", "deaths"])
    @Player.poisoned()
    async def sloth_actions(self, ctx, member: discord.Member = None) -> None:
        """ Shows the status for Sloth Actions.
        :param member: The member to show it from. [Default = You] """

        author = ctx.author
        member = member if member else author
        sloth_actions = await self.get_sloth_actions(member.id, check_target=True)
        divorces = len([sa[1] for sa in sloth_actions if sa[0] == "divorce"])
        transfers = len([sa[1] for sa in sloth_actions if sa[0] == "transfer" and sa[1] == member.id])
        baby_deaths = len([sa[1] for sa in sloth_actions if sa[0] == "baby_death" and sa[1] == member.id])
        pet_deaths = len([sa[1] for sa in sloth_actions if sa[0] == "pet_death" and sa[1] == member.id])

        actions_map = (
            {"text": "divorces", "emoji": "💔", "count": divorces},
            {"text": "money transfers", "emoji": "💸", "count": transfers},
            {"text": "baby deaths", "emoji": "👶", "count": baby_deaths},
            {"text": "pet deaths", "emoji": "🥚", "count": pet_deaths},
        )

        description = "\n".join([f"{a['count']} {a['text']} {a['emoji']}" for a in actions_map])
        embed = discord.Embed(
            title=f"Sloth Actions",
            description=f"```{description}```",
            timestamp=ctx.message.created_at,
            color=ctx.author.color
        )
        embed.set_author(name=member, icon_url=member.display_avatar)
        embed.set_footer(text=f"Requested by: {author}", icon_url=author.display_avatar)
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(SlothReputation(client))
