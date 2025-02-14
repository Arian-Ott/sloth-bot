# import.standard
import io
import os
from datetime import timedelta
from typing import List

# import.thirdparty
import discord
from discord import utils
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

# import.local
from extra import utils
from extra.analytics import DataBumpsTable, SlothAnalyticsTable
from mysqldb import DatabaseCore

# variables.textchannel
bots_and_commands_channel_id = int(os.getenv('BOTS_AND_COMMANDS_CHANNEL_ID', 123))
join_leave_log_channel_id = int(os.getenv('JOIN_LEAVE_LOG_CHANNEL_ID', 123))

analytics_cogs: List[commands.Cog] = [SlothAnalyticsTable, DataBumpsTable]

class Analytics(*analytics_cogs):
    """ A cog related to the analytics of the server. """

    def __init__(self, client) -> None:
        """ Class initializing method. """

        self.client = client
        self.dnk_id: int = int(os.getenv('DNK_ID', 123))
        self.db = DatabaseCore()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """ Tells when the cog's ready to be used. """

        print("Analytics cog is online!")
        self.check_midnight.start()

    @tasks.loop(minutes=1)
    async def check_midnight(self) -> None:
        """ Checks whether it's midnight. """

        time_now = await utils.get_time_now()
        day = time_now.day
        if await self.check_relatory_time(day):
            channel = self.client.get_channel(bots_and_commands_channel_id)
            if not channel:
                return
            members = channel.guild.members
            info = await self.get_info()
            online_members = [om for om in members if str(om.status) == "online"]
            small = ImageFont.truetype("built titling sb.ttf", 45)
            analytics = Image.open("./png/analytics.png").resize((500, 600))
            draw = ImageDraw.Draw(analytics)
            draw.text((140, 270), f"{info[0]}", (255, 255, 255), font=small)
            draw.text((140, 335), f"{info[1]}", (255, 255, 255), font=small)
            draw.text((140, 395), f"{info[2]}", (255, 255, 255), font=small)
            draw.text((140, 460), f"{len(members)}", (255, 255, 255), font=small)
            draw.text((140, 520), f"{len(online_members)}", (255, 255, 255), font=small)

            with io.BytesIO() as fp:
                analytics.save(fp, 'png', quality=90)
                fp.seek(0)
                fp = discord.File(fp, filename="analytics_result.png")
                await channel.send(file=fp)

            try:
                await self.reset_table_sloth_analytics_callback()
                complete_date = time_now.strftime('%d/%m/%Y')
                await self.bump_data(info[0], info[1], info[2], len(members), len(online_members), str(complete_date))
            except Exception as e:
                print('SlothAnalytics error', e)

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        """ Tells the newcomer to assign themselves a native language role, sends an embed to the joined-left log and updates the joined members counter. """

        await self.update_joined()

        channel = self.client.get_channel(join_leave_log_channel_id)
        user = await self.client.fetch_user(member.id)
        time = discord.utils.utcnow()

        embed = discord.Embed(
                title="Member Joined",
                description=f"{member.mention} {member.name}",
                color=discord.Colour.green(),
                timestamp=time
            )
        
        account_age = time - member.created_at
        days = account_age.days
        hours, remainder = divmod(account_age.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        embed.add_field(name="**Account Age**", value=f"{days} days, {hours} hours, {minutes} minutes", inline=True)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(text=str(member.id))

        if user.banner:
            embed.set_image(url=user.banner.url)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member) -> None:
        """ Sends an embed to the joined-left log and updates the let members counter. """

        await self.update_left()

        channel = self.client.get_channel(join_leave_log_channel_id)
        user = await self.client.fetch_user(member.id)
        time = discord.utils.utcnow()

        embed = discord.Embed(
                title="Member Left",
                description=f"{member.mention} {member.nick if member.nick else member.name}\n",
                color=discord.Colour.red(),
                timestamp=time
            )
        
        embed.add_field(name="**Joined**", value=f"<t:{int(member.joined_at.timestamp())}:f>", inline=True)
        embed.add_field(name="**Left**", value=f"<t:{int(time.timestamp())}:f>", inline=True)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(text=member.id)

        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            embed.add_field(name="Roles", value=", ".join(roles), inline=False)

        if user.banner:
            embed.set_image(url=user.banner.url)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        """ Updates the messages counter. """

        if not message.guild:
            return

        await self.update_messages()

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def stop_task(self, ctx) -> None:
        """ Stops the midnight-checker task. """

        self.check_midnight.stop()
        return await ctx.send("**Analytics task has been stopped!**", delete_after=3)

    async def growth_percentage(self, present: int, past: int) -> float:
        """ Gets the growth percentage of a value compared to another one.
        :param present: The current value.
        :param past: The old value to which you wanna compare. """

        # PR = Percent Rate
        pr = ((present - past) / past) * 100
        return pr

    async def calculate_monthly(self) -> List[float]:
        """ Calculates, shows and returns the growth percentage rate of all months. """

        pr_list: List[float] = []
        total_month_members = await self.get_monthly_total()
        # print('='*45)
        for i, month in enumerate(total_month_members):
            first_line = f"Month: {i+1} | Total Members: {month}"
            # print(f"{first_line:^45}")
            if i != 0 and (i-1) % 2 == 0 and (i-1) < len(total_month_members):
                pr = await self.growth_percentage(total_month_members[i], total_month_members[i-1])
                pr_list.append(pr)
                # print(f'\tGrowth increase: {pr:.2f}% ({total_month_members[i-1]} → {total_month_members[i]})')
                # print('='*45)

        return pr_list

    async def calculate_daily(self) -> List[float]:
        """ Calculates, shows and returns the growth percentage rate of all days. """

        pr_list: List[float] = []
        total_day_members = await self.get_daily_total()
        # print('='*45)
        for i, day in enumerate(total_day_members):
            first_line = f"Day: {i+1} | Total Members: {day}"
            # print(f"{first_line:^45}")
            if i != 0 and (i-1) % 2 == 0 and (i-1) < len(total_day_members):
                pr = await self.growth_percentage(total_day_members[i], total_day_members[i-1])
                pr_list.append(pr)
                # print(f'\tGrowth increase: {pr:.2f}% ({total_day_members[i-1]} → {total_day_members[i]})')
                # print('='*45)

        return pr_list

    async def get_current_day_and_future_day(self, days: int, hours: int) -> str:
        """ Gets the current day and the future day, by incrementing X days to the current day.
        :param days: The amount of days to be incremented.
        :param hours: The amount of hours to be incremented. """

        time_now = await utils.get_time_now()
        future_date_and_time = time_now + timedelta(days=days, hours=hours)

        last_day = time_now.strftime('%d/%m/%Y at %H')
        future_day = future_date_and_time.strftime('%d/%m/%Y at %H')
        return last_day, future_day

    async def predict_total_members(self, present: int, future: int, pr: float) -> int:
        """ Predicts the total of members in days.
        :param present: The current value.
        :param future: The goal value.
        :param the percentage growth rate. """

        count = 0
        hours = 0
        current_compound = temp_value = present
        # print('-'*20)
        time_now = await utils.get_time_now()

        while True:

            # PR (Percentage Rate)
            pr_compound = (current_compound * pr) / 100

            # Sum of PR and current compound
            sum_both = current_compound + pr_compound

            # Sees whether the sum of PR and current value are >= the future value
            if sum_both >= future:
                pr_divided = pr_compound / 24
                remaining_hours = 24
                if time_now.hour != 0 and count == 0:
                    remaining_hours = 24 - time_now.hour

                # Divides the remaining PR by 24 hours
                remaining_pr = pr_compound / 24

                # Loops through each remaining hour of that day, so the data is hour-precise
                for _ in range(remaining_hours):
                    sum_remaining = current_compound + remaining_pr
                    current_compound = sum_remaining
                    hours += 1

                    # If the current compound is >= the future value, break the loop
                    if sum_remaining >= future:
                        break

                break

            # If none of the conditions are satisfied, starts another iteration of another looping
            current_compound = sum_both
            count += 1

        last_day, future_day = await self.get_current_day_and_future_day(count, hours)
        line1 = f"{'Present:':<8} {present} members. Date: ({last_day})"
        line2 = f"|↓ in {count} day(s) and {hours} hours ↓|"
        line3 = f"{'Future:':<8} {future} members. Date: ({future_day})"
        return f"{line1}\n{line2:^48}\n{line3}"

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def when(self, ctx, future: int = None) -> None:
        """ Estimates and predicts when the server will hit the given amount of members.
        :param future: The goal value. """

        if not future:
            return await ctx.send("**Please, inform a future value (goal value)!**")

        if len(str(future)) > 6:
            return await ctx.send("**Don't try to troll!**")

        # await calculate_monthly()
        pr_list = await self.calculate_daily()
        pr_average = sum(pr_list) / len(pr_list)
        if pr_average <= 0:
            return await ctx.send(f"**I'm afraid I can't calculate it, because you have a negative PR of `{round(pr_average, 2)}%`**")
        # last_record = await self.get_last_members_record()
        last_record = len(ctx.guild.members)

        if last_record >= future:
            return await ctx.send("**It looks like the server already reached that number!**")
        prediction = await self.predict_total_members(
            present=last_record, future=future, pr=pr_average
        )

        embed = discord.Embed(
            title="Future Value Estimation",
            description=f"Considering an average Growth Percentage Rate of `{round(pr_average, 2)}%`",
            color=ctx.author.color,
            timestamp=ctx.message.created_at
        )

        embed.add_field(
            name="="*59,
            value=f"```apache\n{prediction}```**{'='*59}**"
        )

        await ctx.send(embed=embed)


def setup(client):
    """ Cog's setup function. """

    client.add_cog(Analytics(client))
