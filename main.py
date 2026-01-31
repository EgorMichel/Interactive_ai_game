import asyncio
import sys

# This adds the project root to the Python path.
# It allows us to run the game from the root directory and have all imports work correctly.
sys.path.insert(0, '.')

from uin_engine.interface.cli.main import main


if __name__ == "__main__":
    """
    The main entrypoint for the UIN Engine application.
    """
    try:
        print("Starting UIN Engine...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication exited by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

