"""Package entrypoint for `python -m ytce`."""

import sys

from ytce.cli.main import main


if __name__ == "__main__":
    sys.exit(main())
