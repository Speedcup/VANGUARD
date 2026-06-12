# VANGUARD

A single-guild Discord bot for the **VALPAW** community, built with
[discord.py](https://discordpy.readthedocs.io/) 2.x. It provides a semantic FAQ
system, modal-based report forms backed by runtime-editable option sets, news
auto-publishing, member logging, and a honeypot trap for compromised accounts.

This is a ground-up rewrite from interactions.py to discord.py.

## Features

- **FAQ system**
  - An interactive admin panel (`/faqadmin`) to browse, create, edit, and delete
    entries; each entry's question is embedded into pgvector for matching.
  - `/faq` lookup with search-as-you-type autocomplete.
  - An **auto-responder** that replies to ordinary messages when they match a FAQ,
    using a two-stage matcher (RapidFuzz fast-path then pgvector semantic search)
    tuned to stay silent rather than answer wrongly.
  - An **intent nudge** that detects informal bug/suggestion chatter and points the
    user to `/bugreport` or `/suggest`.
- **Modal forms** for Bug Reports, Suggestions, and Help, reachable from both a
  persistent button panel and slash commands (`/bugreport`, `/suggest`, `/help`);
  submissions post as **new forum posts** in the configured forum channels.
  - Bug reports open a polished **device-info step** first: pick your iPhone
    **model**, its **line/variant** (Standard / e / Pro / Pro Max / Plus / mini,
    defaulting to Standard), and your **iOS version** via a two-step
    major → minor picker. All three are stored as separate fields on the report.
- **Managed option sets** (`/options`): all select-menu contents (iPhone models,
  iPhone lines, iOS versions, suggestion categories, ...) are database-backed and
  editable at runtime with zero code changes — including a per-option
  **description** shown beneath the choice in the menu.
- **Announcements**: auto-publishes posts in announcement (news) channels.
- **Member logging**: join / leave / ban messages to a log channel.
- **Honeypot**: trap channels that softban (purge + auto-unban) compromised
  accounts, with a live "caught" counter and a moderator log.

## Requirements

- **Python 3.11 or 3.12** (pinned for reliable `torch` / `sentence-transformers`
  wheels; Python 3.13+ removed the `audioop` module discord.py depends on).
- **PostgreSQL** with the **pgvector** extension available.
- A Discord application/bot with the privileged intents enabled (see below).

## Setup

1. **Clone & install dependencies**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

2. **PostgreSQL + pgvector**

Create a database and ensure the `vector` extension can be installed. The bot
enables it automatically on startup (`CREATE EXTENSION IF NOT EXISTS vector`), but
the extension must be present on the server. On a typical install:

```sql
CREATE DATABASE vanguard;
-- pgvector must be installed at the OS/package level first, e.g.
-- `apt install postgresql-16-pgvector` or via the official docker image
-- `pgvector/pgvector:pg16`.
```

The schema (tables + indexes) and initial seed data are created idempotently on
every startup, so there's no separate migration step.

3. **Configure environment**

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | yes | Bot token. |
| `GUILD_ID` | yes | The guild commands are synced to. |
| `STAFF_ROLE_ID` | yes | Role that gates all management commands. |
| `DATABASE_URL` | yes | PostgreSQL DSN (`postgresql://user:pass@host:5432/db`). |
| `EMBEDDING_MODEL` | no | sentence-transformers model (default `all-MiniLM-L6-v2`). |
| `BUG_REPORT_CHANNEL_ID` | no | Forum (or text) channel for bug reports (falls back to `REPORTS_CHANNEL_ID`). |
| `SUGGESTION_CHANNEL_ID` | no | Forum (or text) channel for suggestions. |
| `HELP_CHANNEL_ID` | no | Forum (or text) channel for help requests. |
| `REPORTS_CHANNEL_ID` | no | Shared fallback (forum or text) channel for forms. |
| `MEMBER_LOG_CHANNEL_ID` | no | Join/leave/ban logs. |
| `MOD_LOG_CHANNEL_ID` | no | Honeypot catch log. |
| `FAQ_SIMILARITY_THRESHOLD` | no | Seed cosine threshold (default `0.62`). |
| `FAQ_FUZZY_THRESHOLD` | no | Seed RapidFuzz threshold (default `90`). |
| `FAQ_COOLDOWN_SECONDS` | no | Seed auto-responder cooldown (default `60`). |
| `FAQ_MIN_MESSAGE_LENGTH` | no | Seed minimum message length (default `15`). |
| `HONEYPOT_SOFTBAN_SECONDS` | no | Seed softban duration (default `60`). |
| `DEBUG` | no | `1` for verbose logging. |

The `FAQ_*` and `HONEYPOT_*` values are only **seeds**: after the first run they
live in the `bot_settings` table and are changed via staff commands
(`/faqconfig`, `/honeypot`).

4. **Run**

```bash
python index.py
```

Or with Docker (the included `Dockerfile` uses `python:3.12`):

```bash
docker build -t vanguard .
docker run --env-file .env vanguard
```

## Required intents & permissions

Enable these **privileged intents** in the Discord Developer Portal:

- **Message Content Intent** — required for the FAQ auto-responder and honeypot trigger.
- **Server Members Intent** — required for member join/leave logging.

Recommended bot permissions:

- Send Messages, Embed Links, Read Message History, Add Reactions
- **Create Posts** + Send Messages in Threads (forum channels for form submissions)
- Manage Messages (announcements + honeypot)
- **Ban Members** (honeypot softban)
- Manage Messages in announcement channels (to publish)

## How it works

### Persistence & lifecycle

All state lives in PostgreSQL via an `asyncpg` pool (`db/pool.py`). On
`setup_hook` the bot creates the pool, runs the idempotent schema init
(`db/schema.py`), loads the embedding model, loads every cog, registers the
persistent views (so the forms panel and honeypot counter survive restarts), and
syncs application commands to the configured guild.

### FAQ matching

The auto-responder (`cogs/faq.py` + `services/matcher.py`) runs on each eligible
message:

1. **Safeguards** — ignores bots, messages below the minimum length, opt-out
   channels, and per-user/channel cooldowns.
2. **Stage 1 (RapidFuzz)** — a cheap `token_set_ratio` over FAQ questions catches
   near-exact phrasing without touching the model or the DB.
3. **Stage 2 (pgvector)** — otherwise the message is embedded locally and compared
   by cosine similarity; a match must clear the configured threshold or the bot
   stays silent.

Thresholds, cooldown, minimum length, and opt-out channels are all runtime-
configurable via `/faqconfig`.

### FAQ admin panel

`/faqadmin` opens an ephemeral panel: a select menu (paginated past 25 entries)
picks an entry, and buttons let staff **Modify** the answer, **Edit Details**
(question/category), **Delete** (with confirmation), or create a **New Entry**.

Modify is reply-based to preserve long, formatted answers: pressing it posts a
normal message ("reply to this with the new answer") and persists the
message-to-entry link in `faq_edit_prompts`. When the same admin replies, the
listener copies the reply's **raw content verbatim** into the answer and re-embeds
the question. Because the linkage lives in the DB, it survives restarts with no
timer. (Editing the answer doesn't change matching, which is driven by the
question's embedding; editing the question re-embeds.)

### Intent nudge

When a message isn't a FAQ match, a heuristic classifier
(`services/intent_classifier.py`) checks for informal bug/suggestion phrasing and,
if confident, replies pointing the user to `/bugreport` or `/suggest`. It reuses
the FAQ safeguards (bots, minimum length, opt-out channels), skips the report
forums themselves, and has its own cooldown. Toggle and cooldown live under
`/nudge`.

### Option sets

`option_set_items` is a single generic table keyed by `set_name` (with optional
per-option `description`). Every select menu reads live from it at interaction
time, so adding an iPhone model or a new iOS point release is just `/options add`.
Options have a display order and an enabled flag, so they can be **retired without
deletion** (keeping historical reports intact). Menus paginate automatically when
a set exceeds Discord's 25-option limit (the last/first slots become
Next/Previous controls that flip pages in place).

The device sets (`iphone_model`, `iphone_line`, `ios_version`) are seeded from a
**versioned migration** (`CURRENT_SEED_VERSION` in `db/schema.py`): bumping the
version re-applies the canonical lists exactly once, so the model/line/version
data can evolve in code without clobbering staff edits on every restart. iOS
versions hold individual minor releases (e.g. `17.0`–`17.7`, `18.0`–`18.7`,
`26.0`–`26.5`); the bug flow selects them with a two-step major → minor picker so
each select stays under the 25-option cap.

### Modal forms

Discord modals allow at most 5 components and no select menus, so selectable
fields (iPhone model, line, iOS version, suggestion category) are gathered in a
pre-modal view and carried into the modal. Bug reports use a dedicated,
guidance-rich device-info view (model + line + iOS major → minor) that also tells
the user where to find each value in **Settings › General › About** and why it's
collected; suggestions use the generic pre-modal select. Text fields are
consolidated to fit the 5-component limit.

Submissions post to the configured channel as a branded embed. If that channel is
a **forum channel** (the default for bug reports, suggestions, and help), each
submission creates a **new forum post/thread** titled from the submission's title;
if it's a plain text channel, the embed is posted as a message instead. Note: if a
forum requires a tag to be selected, posting will fail and the submitter is told to
notify staff. The bot needs **Create Posts** (and Send Messages in Threads) in the
forum.

### Honeypot

Staff designate trap channels with `/honeypot setup`. A warning embed is posted
with a permanently-disabled button that acts as a live "caught" counter. When a
non-exempt user posts in a trap, the bot **softbans** them (`ban` with
`delete_message_seconds=3600` to purge their last hour of messages, then an
automatic unban after a configurable delay) and logs the catch. Bots, staff,
exempt roles, and anyone with ban/admin/manage-guild permissions are never
caught. Softban duration and an optional DM-on-unban heads-up are configurable
via `/honeypot`.

## Project layout

```
index.py            Entry point.
bot/                Config, logging, and the Bot subclass (setup_hook).
db/                 Connection pool + idempotent schema/seeds.
repositories/       Data-access layer (one per concern).
services/           Embedding model + two-stage matcher.
cogs/               Feature cogs (faq, forms, option_sets, announcements, members, honeypot).
ui/                 Embeds, views, modals, and the live option select.
utils/              Staff check + centralized command error handler.
```
