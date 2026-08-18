from pathlib import Path

import aiosqlite


DATABASE_PATH = Path("data/economy.db")


async def init_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:

        # =========================
        # Players
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                total_jobs INTEGER NOT NULL DEFAULT 0,
                total_earned INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =========================
        # Wallets
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER UNIQUE NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (player_id)
                    REFERENCES players(id)
            )
        """)

        # =========================
        # Transactions
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (wallet_id)
                    REFERENCES wallets(id)
            )
        """)

        # =========================
        # Job Cooldowns
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS job_cooldowns (
                player_id INTEGER NOT NULL,
                job_id TEXT NOT NULL,
                last_work_at INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (player_id, job_id),

                FOREIGN KEY (player_id)
                    REFERENCES players(id)
            )
        """)

        # =========================
        # Businesses
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                business_type TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_income_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(player_id, business_type),

                FOREIGN KEY (player_id)
                    REFERENCES players(id)
            )
        """)

        # =========================
        # Database Migration
        # =========================

        cursor = await db.execute(
            "PRAGMA table_info(players)"
        )

        columns = await cursor.fetchall()

        column_names = {
            column[1]
            for column in columns
        }

        if "total_jobs" not in column_names:
            await db.execute("""
                ALTER TABLE players
                ADD COLUMN total_jobs INTEGER NOT NULL DEFAULT 0
            """)

        if "total_earned" not in column_names:
            await db.execute("""
                ALTER TABLE players
                ADD COLUMN total_earned INTEGER NOT NULL DEFAULT 0
            """)

        await db.commit()