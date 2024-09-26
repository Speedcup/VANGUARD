from interactions import Extension, listen, GuildText
from interactions.api.events import MemberAdd, MemberRemove


class Members(Extension):
    log_channel: GuildText = None

    async def async_start(self):
        self.log_channel = await self.client.fetch_channel(
            channel_id=self.client.debug
            and "1275866594152812575"
            or "1235170440578863104"
        )

    @listen(MemberAdd)
    async def on_join(self, event: MemberAdd):
        member = event.member

        await self.log_channel.send(
            content=f"<:icons_join:1275889849009836082> {member.mention} ({member.display_name}) has joined!"
        )

    @listen(MemberRemove)
    async def on_leave(self, event: MemberRemove):
        member = event.member

        # Does not work the way I like, kicks are only (somehow?!) logged when a reason has been provided.
        # After all, this fetch is called too early or too fast so it does not catch the entry even when it exists.
        # I may change the whole "log" thing here, because I'll use commands to sanction members anyway.
        # if kick := await member.guild.fetch_audit_log(user_id=member.id, action_type=AuditLogEventType.MEMBER_KICK, limit=1):
        #     print(kick.users)
        #     print(kick.entries)
        #     if logEntry := kick.entries.:
        #         return await channel.send(content=f"<:icons_kick:1275893750283112488> {member.mention} ({member.display_name}) got kicked by <@{logEntry.user_id}>!"
        #                                           f"{logEntry.reason is not None and '```' + logEntry.reason + '```' or ""}")

        # Should be alright, no? If we have a valid ban record upon leave, they left because of the ban.
        if (ban := await member.guild.fetch_ban(user=member)) is not None:
            ban_reason = f"```{ban.reason}```" if ban.reason else ""

            return await self.log_channel.send(
                content=f"<:icons_ban:1275889713890201620> {member.mention} ({member.display_name}) got banned!"
                f"{ban_reason}"
            )

        await self.log_channel.send(
            content=f"<:icons_leave:1275889855649550356> {member.mention} ({member.display_name}) has left!"
        )
