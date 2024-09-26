from interactions import Extension, slash_command, SlashContext
from models.discord.Embed import Embed


class RateApp(Extension):
    @slash_command(
        name="rate_app", description="Get a link to rate the app on the app store!"
    )
    async def rate_app(self, context: SlashContext):
        await context.send(
            embed=Embed(
                title="✨ Support VALPAW by Leaving a Review! ✨",
                description="Enjoying VALPAW? We’d love to hear your feedback! Your reviews help us improve and reach more users.\n\n"
                "[Click here](https://apps.apple.com/app/id6476132885?action=write-review) to rate and review VALPAW on the App Store!",
            ),
            ephemeral=True,
        )
