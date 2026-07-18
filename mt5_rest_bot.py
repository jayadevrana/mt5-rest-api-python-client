#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


WORKSPACE = Path("/Users/jayadevrana/Documents/New project")
REPO_ROOT = Path("/Users/jayadevrana/Downloads/mt5-rest-api-main")
WINE_PREFIX = Path.home() / "Library/Application Support/net.metaquotes.wine.metatrader5"
MT5_ROOT = WINE_PREFIX / "drive_c/Program Files/MetaTrader 5"
MT5_MQL5 = MT5_ROOT / "MQL5"
MT5_CONFIG = MT5_ROOT / "config"
TERMINAL_EXE = MT5_ROOT / "terminal64.exe"
WINE64 = Path("/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine64")
WINESERVER = Path("/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wineserver")
REST_EXPERT_DIR = MT5_MQL5 / "Experts/RestApi"
REST_EXPERT_NAME = "RestApi\\RestApi.ex5"
REST_CONFIG_PATH = MT5_CONFIG / "restapi_startup.ini"
REST_SET_PATH = MT5_CONFIG / "restapi.set"
REST_HOST = "127.0.0.1"
REST_PORT = 6542
AUTH_TOKEN = "{test-token}"


def install_rest_api() -> None:
    source_mql5 = REPO_ROOT / "MQL5"
    if not source_mql5.exists():
        raise FileNotFoundError(f"Missing repo: {source_mql5}")

    REST_EXPERT_DIR.mkdir(parents=True, exist_ok=True)
    (MT5_MQL5 / "Include").mkdir(parents=True, exist_ok=True)
    (MT5_MQL5 / "Libraries").mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_mql5 / "Experts/Advisors/RestApi.ex5", REST_EXPERT_DIR / "RestApi.ex5")
    shutil.copy2(source_mql5 / "Experts/Advisors/RestApi.mq5", REST_EXPERT_DIR / "RestApi.mq5")
    shutil.copy2(source_mql5 / "Include/RestApi.mqh", MT5_MQL5 / "Include/RestApi.mqh")
    shutil.copy2(source_mql5 / "Include/json.mqh", MT5_MQL5 / "Include/json.mqh")

    for dll_path in (source_mql5 / "Libraries").iterdir():
        if dll_path.is_file():
            shutil.copy2(dll_path, MT5_MQL5 / "Libraries" / dll_path.name)


def write_startup_config(symbol: str = "BTCUSD", period: str = "M1") -> Path:
    write_expert_set_file()
    content = "\r\n".join(
        [
            "[Charts]",
            "ProfileLast=Default",
            "PreloadCharts=1",
            "",
            "[Experts]",
            "AllowLiveTrading=1",
            "AllowDllImport=1",
            "Enabled=1",
            "",
            "[StartUp]",
            f"Expert={REST_EXPERT_NAME}",
            f"ExpertParameters={REST_SET_PATH.name}",
            f"Symbol={symbol}",
            f"Period={period}",
            "",
        ]
    )
    REST_CONFIG_PATH.write_text(content, encoding="utf-16")
    return REST_CONFIG_PATH


def write_expert_set_file() -> Path:
    content = "\r\n".join(
        [
            "; RestApi expert inputs",
            "; name=value||start||step||stop||selected",
            f"host=http://{REST_HOST}||0||0||0||N",
            f"port={REST_PORT}||0||0||0||N",
            "commandWaitTimeout=10||0||0||0||N",
            "callbackUrl=http://127.0.0.1/callback||0||0||0||N",
            "callbackFormat=json||0||0||0||N",
            f"url_swagger={REST_HOST}:{REST_PORT}||0||0||0||N",
            "CommandPingMilliseconds=10||0||0||0||N",
            f"AuthToken={AUTH_TOKEN}||0||0||0||N",
            "",
        ]
    )
    REST_SET_PATH.write_text(content, encoding="utf-16")
    return REST_SET_PATH


def windows_path(path: Path) -> str:
    posix = str(path)
    if posix.startswith("/"):
        return "Z:" + posix.replace("/", "\\")
    return posix.replace("/", "\\")


def is_api_up(timeout_seconds: int = 2) -> bool:
    try:
        request = Request(
            f"http://{REST_HOST}:{REST_PORT}/info",
            headers={"Authorization": AUTH_TOKEN},
            method="GET",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except Exception:
        return False


def quit_mt5_processes() -> None:
    subprocess.run(["pkill", "-f", "terminal64.exe"], check=False)
    subprocess.run(
        [str(WINESERVER), "-k"],
        env={"WINEPREFIX": str(WINE_PREFIX)},
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)


def launch_mt5_with_rest(symbol: str, restart_terminal: bool) -> None:
    install_rest_api()
    config_path = write_startup_config(symbol=symbol)

    if restart_terminal:
        quit_mt5_processes()

    subprocess.Popen(
        [
            str(WINE64),
            str(TERMINAL_EXE),
            f"/config:{windows_path(config_path)}",
        ],
        env={"WINEPREFIX": str(WINE_PREFIX)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_api(timeout_seconds: int = 25) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_api_up():
            return True
        time.sleep(1)
    return False


def http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Authorization": AUTH_TOKEN}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"http://{REST_HOST}:{REST_PORT}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    except URLError as exc:
        raise RuntimeError(f"REST API unavailable: {exc.reason}") from exc


def load_trade_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json and args.json_file:
        raise ValueError("Use either --json or --json-file, not both.")
    if args.json:
        payload = json.loads(args.json)
    elif args.json_file:
        payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    else:
        payload = {
            "symbol": args.symbol,
            "actionType": f"ORDER_TYPE_{args.action.upper()}",
            "volume": args.volume,
            "comment": args.comment,
        }

    if "symbol" not in payload or "actionType" not in payload or "volume" not in payload:
        raise ValueError("Trade payload must include symbol, actionType, and volume.")
    return payload


def ensure_api(args: argparse.Namespace, symbol: str) -> None:
    if is_api_up():
        return
    launch_mt5_with_rest(symbol=symbol, restart_terminal=args.restart_terminal)
    if not wait_for_api():
        raise RuntimeError(
            "MT5 REST API did not start. If MT5 is open, rerun with --restart-terminal "
            "or verify the terminal logged in successfully."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local MT5 REST bot for the Vantage demo terminal.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser("info", help="Install/start the MT5 REST API and fetch account info.")
    info_parser.add_argument("--restart-terminal", action="store_true", help="Restart MT5 before launching the REST EA.")
    info_parser.add_argument("--symbol", default="BTCUSD", help="Startup chart symbol used to host the REST EA.")

    trade_parser = subparsers.add_parser("trade", help="Install/start the MT5 REST API and place a trade.")
    trade_parser.add_argument("--restart-terminal", action="store_true", help="Restart MT5 before launching the REST EA.")
    trade_parser.add_argument("--symbol", default="BTCUSD", help="Symbol for direct argument mode.")
    trade_parser.add_argument("--action", default="BUY", choices=["BUY", "SELL"], help="Trade direction for direct argument mode.")
    trade_parser.add_argument("--volume", type=float, default=0.01, help="Trade volume for direct argument mode.")
    trade_parser.add_argument("--comment", default="REST demo order", help="Comment for direct argument mode.")
    trade_parser.add_argument("--json", help="Inline JSON payload for /trade.")
    trade_parser.add_argument("--json-file", help="JSON file payload for /trade.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "info":
            ensure_api(args, symbol=args.symbol)
            print(json.dumps(http_json("GET", "/info"), indent=2))
            return 0

        if args.command == "trade":
            payload = load_trade_payload(args)
            ensure_api(args, symbol=str(payload["symbol"]))
            print(json.dumps(http_json("POST", "/trade", payload), indent=2))
            return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
