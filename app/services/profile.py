from typing import Optional

from app.services.player import get_player


async def get_profile(telegram_id: int) -> Optional[dict]:
    """Profile reads the same player document, no second query needed."""
    return await get_player(telegram_id)
