# MT5 REST API Python Client

Python client and launcher for driving MetaTrader 5 through a local REST API Expert Advisor — it auto-installs the EA, restarts the terminal with a generated startup config, and places trades over HTTP.

## Features

- One-command bootstrap: installs the REST API EA (`RestApi.ex5`), its includes, and DLLs into the local MT5 terminal.
- Generates the MT5 startup `.ini` and expert `.set` files so the terminal auto-loads the REST EA on launch.
- Restarts the MT5 terminal (Wine-based on macOS) cleanly via `pkill` / `wineserver -k`.
- Waits for the REST API to come up before issuing requests.
- `info` command fetches live account info from the terminal.
- `trade` command places market orders by direct CLI args, inline JSON, or a JSON payload file.
- Reusable JSON payloads for repeatable BUY/SELL orders.
- Zero third-party dependencies — pure Python standard library (`urllib`, `argparse`, `subprocess`).

## Stack

- Python 3 (standard library only)
- MetaTrader 5 + an MQL5 REST API Expert Advisor
- macOS via the MetaQuotes Wine build of MT5 (paths are configurable for other setups)

## Getting started

Requires Python 3.9+ and a working MetaTrader 5 install. Point the path constants at the top of `mt5_rest_bot.py` (workspace, MT5 root, Wine binaries, REST EA source repo, host/port, auth token) at your own environment first.

Fetch account info (installing/starting the REST EA if needed):

```bash
python3 mt5_rest_bot.py info --restart-terminal
```

Place a market order via CLI arguments:

```bash
python3 mt5_rest_bot.py trade \
  --action BUY \
  --symbol BTCUSD \
  --volume 0.01 \
  --restart-terminal
```

Place a market order from a JSON payload file:

```bash
python3 mt5_rest_bot.py trade \
  --json-file payloads/buy_btcusd_demo.json \
  --restart-terminal
```

## Notes

Trading automation is infrastructure, not financial advice. No profit guarantees. Test in dry-run/paper before live.

## Author

Built by [Jayadev Rana](https://jayadevrana.in) — @bluealgocapital · [YouTube](https://www.youtube.com/@jayadevrana3657) · [GitHub](https://github.com/jayadevrana)
