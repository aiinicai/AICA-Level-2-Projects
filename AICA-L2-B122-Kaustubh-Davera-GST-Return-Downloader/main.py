"""GST Return Downloader - start here."""
import os
import sys

import webview

from api import Api
from settings import resource_dir


def main():
    api = Api()
    index = os.path.join(resource_dir(), "ui", "index.html")
    window = webview.create_window(
        "GST Downloader",
        url=index,
        js_api=api,
        width=1320,
        height=860,
        min_size=(1100, 720),
        background_color="#F4F6F8",
    )
    api._window = window
    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
