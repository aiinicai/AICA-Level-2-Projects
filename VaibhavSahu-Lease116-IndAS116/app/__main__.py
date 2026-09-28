import sys

from .main import run

if __name__ == "__main__":
    run(open_browser="--no-browser" not in sys.argv)
