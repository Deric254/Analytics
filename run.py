#!/usr/bin/env python3
"""
DericBI Analytics Engine — Local Run Script
============================================
Usage:
    python run.py            # starts on http://localhost:10000
    python run.py --port 8050
    python run.py --debug
"""

import os
import sys
import subprocess
import argparse

REQUIRED = [
    "dash",
    "dash-bootstrap-components",
    "plotly",
    "pandas",
    "numpy",
    "sqlalchemy",
    "pymysql",
    "psycopg2-binary",
    "openpyxl",
    "reportlab",
    "requests",
]


def check_python_version():
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required. You have {sys.version}")
        sys.exit(1)


def install_requirements():
    print("Installing / verifying dependencies (this may take a minute the first time)...")
    for pkg in REQUIRED:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"  WARNING: could not install {pkg}: {result.stderr.strip()[:120]}")
            else:
                print(f"  OK  {pkg}")
        except Exception as e:
            print(f"  SKIP {pkg}: {e}")
    print()


def check_imports():
    """Return list of packages that still can't be imported after install."""
    mapping = {
        "dash": "dash",
        "dash-bootstrap-components": "dash_bootstrap_components",
        "plotly": "plotly",
        "pandas": "pandas",
        "numpy": "numpy",
        "sqlalchemy": "sqlalchemy",
        "pymysql": "pymysql",
        "openpyxl": "openpyxl",
        "reportlab": "reportlab",
        "requests": "requests",
    }
    missing = []
    for pkg, import_name in mapping.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    return missing


def main():
    parser = argparse.ArgumentParser(description="Run DericBI Analytics Engine")
    parser.add_argument("--port",    type=int, default=10000)
    parser.add_argument("--host",    type=str, default="127.0.0.1")
    parser.add_argument("--debug",   action="store_true")
    parser.add_argument("--install", action="store_true", help="Force re-install all packages")
    args = parser.parse_args()

    check_python_version()

    # Always check; install if anything missing or --install forced
    missing = check_imports()
    if missing or args.install:
        if missing:
            print(f"Missing packages: {', '.join(missing)}")
        install_requirements()
        # Recheck
        still_missing = check_imports()
        if still_missing:
            print(f"\nERROR: Could not install: {', '.join(still_missing)}")
            print("Try manually:  pip install " + " ".join(still_missing))
            sys.exit(1)

    os.environ["HOST"]  = args.host
    os.environ["PORT"]  = str(args.port)
    os.environ["DEBUG"] = "true" if args.debug else "false"

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print()
    print("=" * 54)
    print("  DericBI Analytics Engine")
    print("=" * 54)
    print(f"  URL  : http://{args.host}:{args.port}")
    print(f"  Debug: {args.debug}")
    print("  Stop : Ctrl+C")
    print("=" * 54)
    print()

    from app import app
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
