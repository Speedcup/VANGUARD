from models.discord.embed import Embed

from typing import TypeVar, Callable

from interactions.client.const import AsyncCallable
from interactions import (
    Extension,
    SlashCommand,
    SlashContext,
    OptionType,
    Cooldown,
    Buckets,
    BaseCommand,
    slash_option,
)

CommandT = TypeVar("CommandT", BaseCommand, AsyncCallable)


def default_cooldown(
    bucket: Buckets = Buckets.DEFAULT, rate: int = 1, interval: float = 60
) -> Callable[[CommandT], CommandT]:
    def wrapper(coro: CommandT) -> CommandT:
        cooldown_obj = Cooldown(bucket, rate, interval)

        coro.cooldown = cooldown_obj

        return coro

    return wrapper


class FAQ(Extension):
    base = SlashCommand(name="faq", description="Frequently Asked Questions")

    @base.subcommand(
        sub_cmd_name="security",
        sub_cmd_description="Is It Safe to Log In with VALPAW?",
    )
    @slash_option(
        name="short",
        description="Short Version of the FAQ Answer.",
        opt_type=OptionType.BOOLEAN,
        required=False,
    )
    # @default_cooldown()
    async def security_embed(self, context: SlashContext, short: bool = False):
        embed_title: str = (
            "<:icons_locked:1275889862914080849> Is It Safe to Log In with VALPAW?"
        )

        short_embed: str = (
            f"We understand you might have security questions. Here’s a brief overview to help you feel confident using VALPAW:\n"
            f"- **How We Protect Your Data:** VALPAW uses session cookies, securely stored in Apple Keychain, and never handles your personal credentials. Your Riot ID and session cookies are encrypted for maximum protection. [Learn more about how Keychain protects your information.](https://support.apple.com/en-us/102651)\n"
            f"- **Data Use:** We facilitate secure communication between your Apple device and Riot’s servers, with no sharing to third parties.\n"
            f"- **Try VALPAW with Confidence:** Start with a secondary account to experience the app’s features and security without affecting your main account."
        )

        long_embed: str = (
            f"We understand you may have questions about security. Here’s a clear and detailed explanation to help you feel confident using VALPAW:\n"
            f"### <:icons_1:1283516322839400479> How VALPAW Keeps Your Data Safe\n"
            f"- **Secure Login Process:** This means VALPAW never handles your personal credentials or sensitive information. Instead, we use session cookies for authentication, seamlessly managed and stored in your Apple Keychain for added security.\n"
            f"- **Data Encryption:** Your Riot ID and session cookies are safeguarded with advanced encryption, stored securely in Apple Keychain. VALPAW never retains or accesses your sensitive credentials, ensuring your data remains private and protected. [Learn more about how Keychain protects your information.](https://support.apple.com/en-us/102651)\n"
            f"### <:icons_2:1283516328354775121> How Your Data is Used\n"
            f"- **Communication Only:** VALPAW facilitates secure communication exclusively between your Apple device and Riot's official servers. Your data is utilized solely for this purpose and only when you're actively using the app or have background fetch enabled for notifications.\n"
            f"- **No Third-Party Sharing:** We adhere to stringent policies to ensure your data is never shared with VALPAW, third parties, or other devices. Your privacy is paramount and remains our top priority.\n"
            f"### <:icons_3:1283516334063485113> Not Sure About VALPAW?\n"
            f"- **Try a Secondary Account:** If you have reservations, consider starting with a secondary account. This allows you to explore VALPAW’s functionality and security without impacting your primary account.\n"
            f"- **Trust and Safety:** Your confidence is important to us. VALPAW is crafted with a focus on your security, ensuring a safe and reliable experience.\n\n"
            f"**TL;DR:** VALPAW prioritizes your security by leveraging Apple Keychain to safeguard your Riot ID and session cookies. We never have access to any sensitive data or information at any time, nor do we require it to provide our services. Feel free to test the app with a secondary account if you’re uncertain.\n\n"
            f"If you have any additional questions or need further assistance, please don’t hesitate to reach out!"
        )

        await context.send(
            embed=Embed(
                title=embed_title, description=short and short_embed or long_embed
            )
        )

    @base.subcommand(
        sub_cmd_name="tos",
        sub_cmd_description="Isn't this against Riot's Terms of Service?",
    )
    # @default_cooldown()
    async def tos_embed(self, context: SlashContext):
        embed_title: str = (
            "<:icons_questionmark:1275889904483696640> Isn't this against Riot's Terms of Service?"
        )

        embed_text: str = (
            f"### <:icons_1:1283516322839400479> Our Commitment to Transparency and Integrity\n"
            f"> Transparency and integrity are at the core of everything we do. When VALPAW was submitted for review, we presented all its features and concepts openly. Riot's approval of the app reflects their trust in our commitment to enhancing the player experience without compromising gameplay integrity.\n"
            f"### <:icons_2:1283516328354775121> Balancing Innovation with Fair Play\n"
            f"> While certain tools may exist in a gray area of Riot's guidelines, we believe that as long as they are used responsibly and do not provide an unfair advantage or harm the game, they are tolerated. For instance, some features that might impact user behavior, like store trackers, are carefully considered. Riot has shown a willingness to accept features that contribute positively to the community while ensuring fair play remains a top priority.\n\n"
            f"VALPAW was designed with these principles in mind. Our app was fully disclosed to Riot and approved because it aligns with their broader values of enhancing the player experience without disrupting the balance of the game. If it hadn’t met these standards, it wouldn’t be available today.\n"
        )

        await context.send(embed=Embed(title=embed_title, description=embed_text))

    @base.subcommand(
        sub_cmd_name="android",
        sub_cmd_description="Is VALPAW available on Android?",
    )
    # @default_cooldown()
    async def android_embed(self, context: SlashContext):
        embed_title: str = (
            "<:icons_wrong:1275889761336430713> Is VALPAW available on android?"
        )

        embed_text: str = (
            f"At this time, VALPAW is exclusively available on iOS. The app is deeply integrated with Apple's exceptional frameworks and internal architecture, which are key to delivering the seamless experience VALPAW offers. Replicating this on Android, with its distinct programming language and platform differences, would compromise the quality and integrity of the app.\n\n"
            f"Our focus remains on providing the best possible experience on iOS, and as such, we have no plans to develop an Android version. Thank you for understanding."
        )

        await context.send(embed=Embed(title=embed_title, description=embed_text))

    @base.subcommand(
        sub_cmd_name="instalocking",
        sub_cmd_description="Can you add the instalocking feature?",
    )
    # @default_cooldown()
    async def instalocking_embed(self, context: SlashContext):
        embed_title: str = (
            "<:icons_mod:1275889869926957169> Can you add the instalocking feature?"
        )

        embed_text: str = (
            f"### <:icons_1:1283516322839400479> Why We Decided Against This\n"
            f"> We’ve carefully considered the idea of a 'softlocking' feature, which would allow users to select an agent without locking them in. However, after thoughtful reflection, we decided not to pursue this functionality. Both locking and selecting agent endpoints are actions that could lead to account bans, and we've seen reports from the Valorant Dev community confirming this risk.\n"
            f"### <:icons_2:1283516328354775121> The Risks of Bannable Features\n"
            f"> While other apps may still offer similar features, even with modifications, it’s important to note that this remains against Riot’s Terms of Service and is a bannable offense. Such features may have avoided detection due to their limited reach, but when similar tools gained broader attention—like with Recon Bolt—Riot took swift action to maintain fairness in the game.\n"
            f"### <:icons_3:1283516334063485113> Commitment to Safe and Fair Gameplay\n"
            f"> Our priority is to provide a safe and enjoyable experience for all players, which is why we’ve chosen not to include any features that could compromise your account or gameplay integrity."
        )

        await context.send(embed=Embed(title=embed_title, description=embed_text))
