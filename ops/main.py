"""Entrypoint for the operations console app (`python -m ops.main`)."""

from ops.tui import OpsConsoleApp


def main():
    app = OpsConsoleApp()
    app.run()


if __name__ == "__main__":
    main()
