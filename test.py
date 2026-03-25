# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main() -> None:
    from agent.main import run_cli
    sys.exit(run_cli())

if __name__ == "__main__":
    main()