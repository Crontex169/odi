# Odi Restaurant Button Watcher

Polls three specific restaurants on [getodi.com](https://getodi.com/student/?city=6) every 10 seconds and pings you on Telegram the moment one of them starts accepting orders (i.e. its order button changes from `class="menu-btn-take disabled"` to `class="menu-btn-take"`).

Restaurants currently watched:

- Queen's Burger (Hacettepe BAM)
- Pilavita City
- Sinyor Chef (Hacettepe)

## How it works

1. **`get_cookies.py`** opens a real Chrome window once. You log in to Odi by hand. Your session cookies get saved to `cookies.json`.
2. **`main.py`** loads those cookies into a `requests.Session`, fetches the page every 10 seconds, parses it with `lxml`, and reads the `class` attribute of each of the three button elements via the exact XPaths you provided.
3. When any button transitions from `disabled` to active, a Telegram message is sent.
4. `state.json` keeps track of the previous state so you don't get duplicate alerts after a restart.

```
get_cookies.py  ->  cookies.json  ->  main.py  ->  watcher loop
                                                       |
                                       (every 10s)     |
                                                       v
                                              scraper.py (HTTP + lxml)
                                                       |
                                                       v
                                              state.py (diff vs state.json)
                                                       |
                                                       v
                                              notifier.py (Telegram API)
                                                       |
                                                       v
                                                Your phone
```

## Prerequisites

- Python 3.10+
- Google Chrome 147 (you already have this; Selenium 4 auto-downloads the matching driver)
- A Telegram account

## Setup

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Create your Telegram bot

1. Open Telegram and search for **`@BotFather`**. Start a chat and send `/newbot`. Pick any name and username for your bot. BotFather will reply with an **HTTP API token** that looks like `123456789:ABCdef...`. Copy it.
2. Open your new bot and send it any message (e.g. `hi`) so it is allowed to write to you.
3. Search for **`@userinfobot`** in Telegram, send `/start`, and copy the numeric **`Id`** value (your chat ID).

### 3. Configure environment variables

Copy the template and fill in your values:

```powershell
copy .env.example .env
notepad .env
```

`.env` should look like:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=123456789
```

### 4. Capture your Odi session cookies

```powershell
python get_cookies.py
```

A Chrome window opens on the Odi login page. **Log in by hand**. When you can see the restaurant list, switch back to your terminal and press **Enter**. The script writes `cookies.json` and closes Chrome.

> If you ever see a Telegram alert that says "cookies expired", just run this command again.

### 5. Start the watcher

```powershell
python main.py
```

You will see a status line every 10 seconds, e.g.:

```
[13:45:02] checked:
  [shut ] Queen's Burger (Hacettepe BAM) (queens_burger)
  [shut ] Pilavita City (pilavita_city)
  [OPEN ] Sinyor Chef (Hacettepe) (sinyor_chef)
```

The first time a button flips from `shut` to `OPEN` between two cycles, you get a Telegram message. Press `Ctrl+C` to stop the watcher.

## Test mode (no Telegram)

You can run the whole watcher locally without spamming your Telegram chat:

```powershell
python main.py --test
```

This is identical to `--console` and prints alerts to the terminal in a banner block instead of sending Telegram messages. Useful while you are tweaking the XPaths or just sanity-checking the polling.

Channel switches:

| Command | Where alerts go |
|---------|-----------------|
| `python main.py`             | Telegram only (default) |
| `python main.py --telegram`  | Telegram only (explicit) |
| `python main.py --test`      | Terminal only (alias of `--console`) |
| `python main.py --console`   | Terminal only |
| `python main.py --both`      | Telegram **and** terminal |

### Fire a single test alert

To verify the full alert path end-to-end without waiting for a real restaurant to open:

```powershell
python test_notify.py             # prints a fake alert to the terminal
python test_notify.py --telegram  # sends a fake alert to your Telegram
python test_notify.py --both      # both
```

If the Telegram variant works, you know your bot token and chat ID are correct.

## Project layout

```
odi/
├── main.py                  # `python main.py [--test|--telegram|--both]`
├── get_cookies.py           # `python get_cookies.py` -> capture session
├── test_notify.py           # `python test_notify.py [--telegram|--both]`
├── config.py                # URL, XPaths, polling interval
├── requirements.txt
├── .env.example             # copy to .env and fill in
├── .gitignore
├── README.md
├── cookies.json             # generated, gitignored
├── state.json               # generated, gitignored
└── src/
    ├── __init__.py
    ├── cookie_helper.py     # Selenium-based cookie capture
    ├── scraper.py           # HTTP + lxml XPath parsing
    ├── notifier.py          # Telegram sendMessage
    ├── console_notifier.py  # stdout printer (test mode)
    ├── notifiers.py         # picks console / telegram / both
    ├── state.py             # state.json + transition diffing
    └── watcher.py           # main polling loop
```

## Customising

All knobs live in `config.py`:

- `URL` - target page
- `POLL_INTERVAL_SECONDS` - currently 10
- `TARGETS` - the list of `{key, name_xpath, button_xpath}` triples. Add or remove restaurants here. Restart the watcher after changing it.

## Troubleshooting

- **`Cookie file not found at ...`** - run `python get_cookies.py` first.
- **`TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set`** - you forgot step 3 above.
- **Telegram alert says "cookies expired"** - your Odi session has timed out. Re-run `python get_cookies.py`, then `python main.py` again.
- **All three buttons stay `shut` forever** - log in to Odi in your normal browser and confirm the restaurants are visible on `https://getodi.com/student/?city=6`. If the page layout has changed, the indices in the XPaths in `config.py` may need updating.
- **`session not created: This version of ChromeDriver only supports Chrome version ...`** - upgrade Selenium: `pip install --upgrade selenium`. Selenium 4.20+ ships with Selenium Manager which auto-handles ChromeDriver for any installed Chrome.

## Security notes

- `cookies.json`, `state.json` and `.env` are listed in `.gitignore` - they contain secrets and should never be committed.
- Your Telegram bot token grants full control of the bot. Don't share it.
