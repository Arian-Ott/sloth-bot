# import.standard
from typing import List, Optional

# import.thirdparty
import discord
from discord.ext import commands

# import.local
from extra import utils
from mysqldb import DatabaseCore

class ModActivityTable(commands.Cog):
    """ Class for managing the ModActivity table in the database. """

    def __init__(self, client: commands.Bot) -> None:
        """ Class init method. """

        self.client = client
        self.db = DatabaseCore()

    # Database commands
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_mod_activity_table(self, ctx) -> None:
        """ (ADM) Creates the ModActivity table. """

        member: discord.Member = ctx.author

        if await self.check_mod_activity_table_exists():
            return await ctx.send(f"**The `ModActivity` table already exists, {member.mention}!**")

        await self.db.execute_query("""
            CREATE TABLE ModActivity (
                mod_id BIGINT NOT NULL,
                time BIGINT DEFAULT 0,
                timestamp BIGINT DEFAULT NULL,
                messages INT DEFAULT 0,
                PRIMARY KEY (mod_id)
            )""")
        await ctx.send(f"**Table `ModActivity` created, {member.mention}!**")
        
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_mod_activity_settings_table(self, ctx) -> None:
        """ (ADM) Creates the ModActivitySettings table. """

        member: discord.Member = ctx.author

        if await self.check_mod_activity_settings_table_exists():
            return await ctx.send(f"**The `ModActivitySettings` table already exists, {member.mention}!**")

        await self.db.execute_query("""
            CREATE TABLE ModActivitySettings (
                min_voice_time BIGINT DEFAULT 10800,
                min_text_messages INT DEFAULT 30
            )""")
        await self.db.execute_query("INSERT INTO ModActivitySettings VALUES(10800, 30)")
        await ctx.send(f"**Table `ModActivitySettings` created, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_mod_activity_table(self, ctx) -> None:
        """ (ADM) Drops the ModActivity table. """

        member: discord.Member = ctx.author
        if not await self.check_mod_activity_table_exists():
            return await ctx.send(f"**The `ModActivity` table doesn't exist, {member.mention}!**")

        await self.db.execute_query('DROP TABLE ModActivity')
        await ctx.send(f"**Table `ModActivity` dropped, {member.mention}!**")
        
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_mod_activity_settings_table(self, ctx) -> None:
        """ (ADM) Drops the ModActivitySettings table. """

        member: discord.Member = ctx.author
        if not await self.check_mod_activity_settings_table_exists():
            return await ctx.send(f"**The `ModActivitySettings` table doesn't exist, {member.mention}!**")

        await self.db.execute_query('DROP TABLE ModActivitySettings')
        await ctx.send(f"**Table `ModActivitySettings` dropped, {member.mention}!**")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_mod_activity_table(self, ctx) -> None:
        """ (ADM) Resets the ModActivity table. """

        member: discord.Member = ctx.author
        if not await self.check_mod_activity_table_exists():
            return await ctx.send(f"**The `ModActivity` table doesn't exist yett, {member.mention}!**")

        await self.db.execute_query("DELETE FROM ModActivity")
        await ctx.send(f"**Table `ModActivity` reset, {member.mention}!**")
        
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_mod_activity_settings_table(self, ctx) -> None:
        """ (ADM) Resets the ModActivitySettings table. """

        member: discord.Member = ctx.author
        if not await self.check_mod_activity_settings_table_exists():
            return await ctx.send(f"**The `ModActivitySettings` table doesn't exist yett, {member.mention}!**")

        await self.db.execute_query("DELETE FROM ModActivitySettings")
        await self.db.execute_query("INSERT INTO ModActivitySettings VALUES(10800, 30)")
        await ctx.send(f"**Table `ModActivitySettings` reset, {member.mention}!**")

    async def check_mod_activity_table_exists(self) -> bool:
        """ Checks whether the ModActivity table exists in the database. """

        return await self.db.table_exists("ModActivity")
    
    async def check_mod_activity_settings_table_exists(self) -> bool:
        """ Checks whether the ModActivitySettings table exists in the database. """

        return await self.db.table_exists("ModActivitySettings")

    async def check_mod_activity_exists(self, mod_id: int) -> bool:
        """ Checks if a moderator already exists in the ModActivity table. """

        mod = await self.db.execute_query("SELECT 1 FROM ModActivity WHERE mod_id = %s", (mod_id,), fetch="one")

        return bool(mod)

    async def insert_moderator(self, mod_id: int, old_ts: Optional[int] = None, messages: Optional[int] = 0) -> None:
        """ Inserts a moderator.
        :param mod_id: The ID of the moderator to insert.
        :param old_ts: The current timestamp. [Optional]
        :param messages: The initial amount of messages for the moderator to start with. [Optional][Default = 0] """

        await self.db.execute_query("""
            INSERT INTO ModActivity (mod_id, timestamp, messages) VALUES (%s, %s, %s)
            """, (mod_id, old_ts, messages))
    async def remove_moderator(self, mod_id: int) -> None:
        """ Removes a moderator from ModActivity table.
        :param mod_id: The ID of the moderator to remove.
        """

        await self.db.execute_query("""
            DELETE FROM ModActivity WHERE mod_id = %s
            """, (mod_id,))

    async def get_mod_activities(self) -> List[List[int]]:
        """ Gets all Mod activities data from the database. """

        return await self.db.execute_query("SELECT * FROM ModActivity ORDER BY time DESC, messages DESC", fetch="all")

    async def get_moderator_current_timestamp(self, mod_id: int, old_ts: Optional[int] = None) -> int:
        """ Gets the moderator's current timestamp.
        :param mod_id: The moderator ID.
        :param old_ts: The current global timestmap. [Optional]"""

        mod = await self.db.execute_query("SELECT * FROM ModActivity WHERE mod_id = %s", (mod_id,), fetch="one")

        if not mod:
            await self.insert_moderator(mod_id, old_ts)
            return await self.get_moderator_current_timestamp(mod_id)

        return mod[2] if mod[2] else old_ts

    async def get_moderator_current_messages(self, mod_id: int) -> int:
        """ Gets the moderator's current amount of messages.
        :param mod_id: The moderator ID. """

        mod = await self.db.execute_query("SELECT * FROM ModActivity WHERE mod_id = %s", (mod_id,), fetch="one")

        if not mod:
            await self.insert_moderator(mod_id, messages=1)
            return await self.get_moderator_current_messages(mod_id)

        return mod[3]

    async def update_moderator_message(self, mod_id: int) -> None:
        """ Updates the moderator's message counter.
        :param mod_id: The moderator's ID. """

        await self.db.execute_query("UPDATE ModActivity SET messages = messages + 1 WHERE mod_id = %s", (mod_id,))

    async def update_moderator_timestamp(self, mod_id: int) -> None:
        """ Updates the moderator's timestamp.
        :param mod_id: The moderator ID. """

        current_ts = await utils.get_timestamp()
        await self.db.execute_query("UPDATE ModActivity SET timestamp = %s WHERE mod_id = %s", (current_ts, mod_id))

    async def update_moderator_time(self, mod_id: int, addition: int) -> None:
        """ Increments the moderator's time counter.
        :param mod_id: The moderator ID.
        :param addition: The addition value. """

        await self.db.execute_query("UPDATE ModActivity SET time = time + %s WHERE mod_id = %s", (addition, mod_id))

    async def reset_mod_activity(self) -> None:
        """ Reset data from the ModActivity table """

        await self.db.execute_query("UPDATE ModActivity SET time = 0, timestamp = 0, messages = 0")

    async def delete_mod_activity(self) -> None:
        """ Deletes all the data from the ModActivity table. """

        await self.db.execute_query("DELETE FROM ModActivity")
        
    async def set_mod_activity_min_text(self, min_text: int) -> int:
        """ Sets the mod activity list's current minimum text message limit.
        :param min_text: The minimum text message limit to set. """

        await self.db.execute_query("UPDATE ModActivitySettings SET min_text_messages = %s", (min_text,))

    async def get_mod_activity_min_text(self) -> int:
        """ Gets the mod activity list's current minimum text message limit. """

        return await self.db.execute_query("SELECT min_text_messages FROM ModActivitySettings", fetch="one")

    async def set_mod_activity_min_voice(self, min_voice: str) -> str:
        """ Sets the mod activity list's current minimum voice time limit.
        :param min_voice: The minimum voice time limit to set. """

        await self.db.execute_query("UPDATE ModActivitySettings SET min_voice_time = %s", (min_voice,))

    async def get_mod_activity_min_voice(self) -> str:
        """ Gets the mod activity list's current minimum voice time limit. """

        return await self.db.execute_query("SELECT min_voice_time FROM ModActivitySettings", fetch="one")
