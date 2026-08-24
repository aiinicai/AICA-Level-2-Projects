import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)

from app.gui import launch_app

if __name__ == "__main__":
    launch_app()
