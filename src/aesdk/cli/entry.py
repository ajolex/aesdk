"""Console-script entry point with a fast path for coding-agent hooks.

Agent hooks run on every shell command or file write, so ``aesdk hook <event>``
is dispatched here without importing Typer or the full CLI (which loads
pandas/statsmodels). Everything else goes to the normal Typer app.
"""

from __future__ import annotations

import sys


def main() -> None:
    argv = sys.argv[1:]
    if argv[:1] == ["hook"] and len(argv) >= 2 and not argv[1].startswith("-"):
        from aesdk.agent.hooks import run_hook

        code, out, err = run_hook(argv[1], sys.stdin.read())
        if out:
            sys.stdout.write(out + "\n")
        if err:
            sys.stderr.write(err + "\n")
        raise SystemExit(code)
    from aesdk.cli.main import app

    app()


if __name__ == "__main__":  # pragma: no cover
    main()
