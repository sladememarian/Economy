# economy

Telegram economy game bot. Runs on MongoDB, wired together with Docker Compose.

## Running

```bash
cp .env.example .env      # then put your BOT_TOKEN in it
docker compose up --build
```

Mongo data survives restarts in the `mongo_data` volume.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite runs on an in memory mongo, so nothing needs to be up. To run it
against the real container instead:

```bash
docker compose up -d mongodb
MONGO_TEST_URI=mongodb://localhost:27017 pytest
```

## Layout

| Path | What it does |
| --- | --- |
| `app/database/mongo.py` | the only place that opens a mongo connection |
| `app/services/economy.py` | every balance change goes through here |
| `app/services/player.py` | player creation, retrieval, xp and levels |
| `app/services/work.py` | jobs, cooldowns, rewards |

Money rules worth knowing before building on top:

- Never write `balance` directly, call `add_money` / `remove_money` / `transfer_money`.
- The wallet lives on the player document, so a balance change and an xp or
  counter change can be done in one atomic write with `also_inc` / `also_set`.
- `remove_money` raises `InsufficientFunds` and leaves the balance untouched.
- Every change appends a line to `transactions`.
