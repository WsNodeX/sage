"""Allow ``python -m sage`` to launch the demo server."""

from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
