import aiosqlite

from app.database.db import DATABASE_PATH


async def get_profile(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                p.id,
                p.telegram_id,
                p.username,
                p.first_name,
                p.level,
                p.xp,
                p.total_jobs,
                p.total_earned,
                w.balance
            FROM players p
            JOIN wallets w ON w.player_id = p.id
            WHERE p.telegram_id = ?
            """,
            (telegram_id,),
        )

        player = await cursor.fetchone()

        if player is None:
            return None

        return dict(player)