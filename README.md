# TestMind Telegram bot

Runs the TestMind personality test inside a Telegram chat: 50 questions, then the
same archetype result the website gives. Answers live only in memory for a
session — nothing is stored or sent anywhere.

## Setup

```
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

Put your bot token (from @BotFather) in **`token.txt`** (one line), or set the
`TELEGRAM_BOT_TOKEN` environment variable. `token.txt` is gitignored — never
commit it.

## Run

```
python bot.py
```

Uses long-polling, so no public server or webhook is needed — it works from any
machine with internet. Open your bot in Telegram and send `/start`.

## Files

- `bot.py` — the bot (commands + question flow + result).
- `testmind_core.py` — scoring, a faithful port of the website's logic.
- `bot_content.json` — the 50 items + archetype content, **generated from the
  website** (`characters.js` + `test.html`) by `_extract.js`, so the bot never
  drifts from the web result.
- `xcheck.py` — proves the Python scoring matches the site's JS on 6000 random
  inputs. Re-run after regenerating `bot_content.json`.

## Regenerate content (if the website's questions/archetypes change)

```
node _extract.js        # rewrites bot_content.json + xcheck.json from the site
python xcheck.py        # must print "PERFECT"
```

## Notes

- v1 stores nothing and has no analytics.
- Session state is in-memory, so it resets if the bot restarts.
- Hosting is TBD — for now `python bot.py` on any always-on machine works.
