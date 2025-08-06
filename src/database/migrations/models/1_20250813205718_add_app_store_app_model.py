from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "appstoreappmodel" (
    "version" TEXT NOT NULL PRIMARY KEY,
    "release_notes" TEXT NOT NULL,
    "release_date" TIMESTAMPTZ NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "appstoreappmodel";"""
