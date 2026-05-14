"""Run AESDK with ``python -m aesdk`` when the console script is not on PATH."""

from aesdk.cli.main import app


if __name__ == "__main__":  # pragma: no cover
    app()
