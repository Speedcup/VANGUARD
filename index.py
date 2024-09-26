import logging
import os
import pkgutil

from interactions import Client, listen, Activity, ActivityType, Intents, Status

logging.basicConfig()
log = logging.getLogger("VANGUARD")
log.setLevel(logging.DEBUG)


class Bot(Client):
    debug: bool = False

    @listen()
    async def on_startup(self):
        log.info(f"Logged in as {self.user.username}")
        await self.change_presence(
            status=Status.ONLINE,
            activity=Activity(name="VALORANT", type=ActivityType.PLAYING),
        )


if __name__ == "__main__":
    bot = Bot(
        activity=Activity(name="Loading…", type=ActivityType.PLAYING),
        intents=Intents.ALL,
        fetch_members=True,
        status=Status.DND,
    )
    bot.debug = bool(os.getenv("DEBUG")) or False

    # Removing automatic updates for now because I need a more stable version control rather than just a file containing the version.
    # Once this has been switched to a database, I can re-activate it.
    extension_blacklist = ["updates"]
    # I am not using the prefix here (prefix="extensions."), because I'd have to remove the extension prefix from everything else other than loading. It is more convenient to add it once in the loading process.
    extension_names = [
        m.name
        for m in pkgutil.iter_modules(["extensions"])
        if m.name not in extension_blacklist
    ]
    for name in extension_names:
        bot.load_extension(f"extensions.{name}")
        log.info(f"Loaded -> {name}")

    bot.start(bot.debug and os.environ["DEV_TOKEN"] or os.environ["TOKEN"])
