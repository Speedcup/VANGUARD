import os
from datetime import datetime

import jwt
import time
import requests

from interactions import (
    Extension,
    GuildText,
    Task,
    IntervalTrigger,
    Embed,
    EmbedAttachment,
    EmbedFooter,
    Button,
    ButtonStyle,
    RoleColors,
    SlashContext,
    slash_command,
    slash_option,
    slash_default_member_permission,
    OptionType,
    Permissions,
)

from models.internal.StoredVersion import StoredVersion
from models.internal.AppStoreRelease import AppStoreRelease
from models.internal.TestFlightRelease import TestFlightRelease


class AppUpdates(Extension):
    log_channel: GuildText = None
    app_id: str = "6476132885"

    new_icon: str = (
        "<:icons_new_1:1276222795457626222><:icons_new_2:1276222802571169824>"
    )
    beta_icon: str = (
        "<:icons_beta_1:1276222778663636993><:icons_beta_2:1276222785814925455>"
    )
    update_icon: str = (
        "<:icons_update_1:1276265952358568038><:icons_update_2:1276265962504589454>"
    )

    localization_icon: str = "<:icons_localization:1276262831049932845>"
    questionmark_icon: str = "<:icons_questionmark:1275889904483696640>"
    hammer_icon: str = "<:icons_hammer:1275889813450526831>"

    async def async_start(self):
        self.log_channel = await self.client.fetch_channel(
            channel_id=self.client.debug
            and "1275866594152812575"
            or "1235170162773069925"
        )
        self.check_app_version.start()

    @Task.create(IntervalTrigger(hours=1))
    async def check_app_version(self, force: bool = False):
        latest_build = self.fetch_release()
        latest_testflight_build = self.fetch_testflight_version()

        stored_versions = StoredVersion.from_cache()

        latest_version = latest_build.version
        latest_testflight_version = latest_testflight_build.version

        if force or (
            latest_version is not None
            and latest_version > stored_versions.release_version
        ):
            await self.log_channel.send(
                embed=Embed(
                    title=f"{self.update_icon} v{latest_version}",
                    description=f"{latest_build.release_notes}\n\n"
                    f"<@&1235207211928784936>",
                    color=RoleColors.GREEN,
                    url=f"https://apps.apple.com/us/app/valpaw/id{self.app_id}",
                    timestamp=latest_build.release_date or datetime.now(),
                    thumbnail=EmbedAttachment(
                        url="https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/4c/6f/df/4c6fdff2-397b-2512-9c96-345ebe20cbd3/AppIcon-0-1x_U007ephone-0-0-85-220-0.png/512x512bb.jpg"
                    ),
                    footer=EmbedFooter(
                        text="App Store",
                        icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/App_Store_%28iOS%29.svg/2048px-App_Store_%28iOS%29.svg.png",
                    ),
                ),
                components=[
                    Button(
                        style=ButtonStyle.LINK,
                        label="Share Your Feedback",
                        url=f"https://apps.apple.com/app/id{self.app_id}?action=write-review",
                        emoji="<:icons_star:1275889934439284839>",
                    )
                ],
            )

        if force or (
            latest_testflight_version is not None
            and latest_testflight_version > stored_versions.testflight_version
        ):
            await self.log_channel.send(
                embed=Embed(
                    title=f"{self.beta_icon} {latest_testflight_build.version}",
                    description=f"A new TestFlight Beta build has just been released and is now available for download!\n"
                    f"### {self.localization_icon} Help Us Improve Localization\n"
                    f"Your feedback on localization is incredibly valuable to us!\n"
                    f"- **Spot an Issue?:** If you notice any translation errors, cultural inaccuracies, or areas where the language could be improved, please let us know.\n"
                    f"- **Suggest Translations:** If you’re fluent in another language and would like to contribute, we’d love your help! You can suggest improvements or translations directly through our [Crowdin project](https://crowdin.com/project/valpaw).\n"
                    f"### {self.questionmark_icon} How to Provide Feedback\n"
                    f"Please share any thoughts, issues, or suggestions you have while using the app:\n"
                    f"- **Bug Reports**: If you encounter any bugs or glitches, report them directly through the TestFlight app. A screenshot and brief description of the issue will be greatly appreciated.\n"
                    f"- **General Feedback**: Any comments on the app’s overall performance, user interface, and usability are welcome.\n\n"
                    f"<@&1279478995863474197>",
                    color=RoleColors.BLUE,
                    url=f"https://apps.apple.com/us/app/valpaw/id{self.app_id}",
                    timestamp=latest_testflight_build.uploadedDate,
                    thumbnail=EmbedAttachment(
                        url="https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/4c/6f/df/4c6fdff2-397b-2512-9c96-345ebe20cbd3/AppIcon-0-1x_U007ephone-0-0-85-220-0.png/512x512bb.jpg"
                    ),
                    footer=EmbedFooter(
                        text="TestFlight",
                        icon_url="https://cdn.jim-nielsen.com/macos/512/testflight-2023-05-19.png?rf=1024",
                    ),
                ),
                components=[
                    Button(
                        style=ButtonStyle.LINK,
                        label="Join Beta",
                        url=f"https://testflight.apple.com/join/eOgMk6SM",
                        emoji="hammer_icon",
                    )
                ],
            )

        stored_versions.release_version = latest_version
        stored_versions.testflight_version = latest_testflight_version
        stored_versions.to_cache()

    def fetch_release(self) -> AppStoreRelease | None:
        url = f"https://itunes.apple.com/lookup?id={self.app_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        data = response.json()

        if data["resultCount"] > 0:
            app_info = data["results"][0]
            data = {
                "version": app_info["version"],
                "release_notes": app_info["releaseNotes"],
                "release_date": app_info["currentVersionReleaseDate"],
            }

            return AppStoreRelease.from_dict(data)

        return None

    def fetch_testflight_version(self) -> TestFlightRelease | None:
        token = self.generate_token()
        url = f"https://api.appstoreconnect.apple.com/v1/preReleaseVersions"

        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "filter[app]": self.app_id,
            "include": "builds",
            "filter[builds.processingState]": "VALID",
            "fields[builds]": "version,uploadedDate,processingState,buildAudienceType",
            "sort": "-version",
            "limit": 10,  # Fetch the latest 10 builds for further filtering
        }

        try:
            builds = requests.get(url, headers=headers, params=params).json()[
                "included"
            ]
            external_build = next(
                build["attributes"]
                for build in builds
                if build["attributes"]["buildAudienceType"] == "APP_STORE_ELIGIBLE"
            )

            return TestFlightRelease.from_dict(external_build)
        except Exception as e:
            return None

    def generate_token(self):
        key_id = os.environ.get("ASC_KEY_ID")
        issuer_id = os.environ.get("ASC_ISSUER_ID")

        with open("AuthKey.p8", "r") as key_file:
            private_key = key_file.read()

        header = {"alg": "ES256", "kid": key_id}
        payload = {
            "iss": issuer_id,
            "exp": int(time.time()) + 1 * 60,  # Token valid for 1 minutes
            "aud": "appstoreconnect-v1",
        }

        token = jwt.encode(payload, private_key, algorithm="ES256", headers=header)

        return token

    @slash_command(name="updates")
    @slash_option(
        name="force",
        description="Whether to force the update, regardless of cached version.",
        opt_type=OptionType.BOOLEAN,
    )
    @slash_default_member_permission(Permissions.ADMINISTRATOR)
    async def send_update(self, context: SlashContext, force: bool = False):
        await self.check_app_version(force=force)
        await context.send("Update sent!", ephemeral=True)
