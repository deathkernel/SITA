"""Command-line entry point for the local SITA interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tara_app.application.bootstrap import RuntimeConfigurationError, create_application
from tara_app.env_loader import load_env_file
from tara_app.webapp import serve


def main() -> int:
    parser = argparse.ArgumentParser(prog="sita", description="Run the local SITA chat interface")
    parser.add_argument("--config", type=Path, default=Path("sita.toml"), help="path to trusted SITA TOML configuration")
    parser.add_argument("--port", type=int, default=8765, help="loopback web port (1024-65535)")
    parser.add_argument(
        "--floating-pet",
        action="store_true",
        help="show the native Windows floating pet instead of the browser interface",
    )
    args = parser.parse_args()
    if args.config == Path("sita.toml") and not args.config.exists() and Path("tara-app.toml").is_file():
        args.config = Path("tara-app.toml")

    app = None
    try:
        # One project-level secret source feeds every Gemini-backed specialist.
        # Existing process environment values take precedence over .env.
        load_env_file(args.config.expanduser().resolve().parent / ".env")
        if args.floating_pet and sys.platform != "win32":
            raise RuntimeConfigurationError("--floating-pet is supported on Windows only")
        app = create_application(args.config)
        startup_warning = app.prepare_runtime()
        if startup_warning:
            print(startup_warning, file=sys.stderr, flush=True)
        if args.floating_pet:
            from tara_app.windows_pet import run_floating_pet
            run_floating_pet(app, port=args.port)
        else:
            serve(app, port=args.port)
    except (RuntimeConfigurationError, OSError, RuntimeError, ValueError) as exc:
        print(f"SITA could not start: {exc}", file=sys.stderr)
        return 2
    finally:
        if app is not None:
            app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
