from typing import Optional

import aiosqlite

from app.database.db import DATABASE_PATH


STARTING_BALANCE = 10_000


async def get_player(telegram_id: int) -> Optional[dict]:
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
                w.id AS wallet_id,
                w.balance
            FROM players p
            JOIN wallets w ON w.player_id = p.id
            WHERE p.telegram_id = ?
            """,
            (telegram_id,),
        )

        row = await cursor.fetchone()

        if row is None:
            return None

        return dict(row)


async def create_player(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
) -> dict:

    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("BEGIN")

            cursor = await db.execute(
                """
                INSERT INTO players (
                    telegram_id,
                    username,
                    first_name
                )
                VALUES (?, ?, ?)
                """,
                (telegram_id, username, first_name),
            )

            player_id = cursor.lastrowid

            cursor = await db.execute(
                """
                INSERT INTO wallets (
                    player_id,
                    balance
                )
                VALUES (?, ?)
                """,
                (player_id, STARTING_BALANCE),
            )

            wallet_id = cursor.lastrowid

            await db.execute(
                """
                INSERT INTO transactions (
                    wallet_id,
                    amount,
                    balance_after,
                    transaction_type,
                    description
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    wallet_id,
                    STARTING_BALANCE,
                    STARTING_BALANCE,
                    "INITIAL_BALANCE",
                    "سرمایه اولیه",
                ),
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    return await get_player(telegram_id)