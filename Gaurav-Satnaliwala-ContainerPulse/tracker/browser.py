from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path


class BrowserUnavailableError(RuntimeError):
    pass


def _candidate_executables() -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []

    # PATH-based discovery also supports macOS/Linux development machines.
    for label, command in [
        ("Google Chrome", "google-chrome"),
        ("Google Chrome", "google-chrome-stable"),
        ("Chromium", "chromium"),
        ("Microsoft Edge", "microsoft-edge"),
        ("Microsoft Edge", "microsoft-edge-stable"),
    ]:
        found = shutil.which(command)
        if found:
            candidates.append((label, Path(found)))

    roots = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    for root in filter(None, roots):
        base = Path(root)
        candidates.extend([
            ("Google Chrome", base / "Google/Chrome/Application/chrome.exe"),
            ("Microsoft Edge", base / "Microsoft/Edge/Application/msedge.exe"),
        ])

    # Useful when a Windows checkout is tested from a shell where the variables
    # above are unavailable.
    candidates.extend([
        ("Google Chrome", Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")),
        ("Google Chrome", Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")),
        ("Microsoft Edge", Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")),
        ("Microsoft Edge", Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")),
    ])
    return candidates


def launch_installed_browser(playwright, headless: bool, logger: logging.Logger):
    """Launch an existing browser without installing/downloading anything."""
    errors: list[str] = []

    for label, channel in [("Google Chrome", "chrome"), ("Microsoft Edge", "msedge")]:
        logger.info("Browser discovery: trying Playwright channel=%s (%s)", channel, label)
        try:
            browser = playwright.chromium.launch(channel=channel, headless=headless)
            logger.info("Browser discovery: launched %s via channel=%s", label, channel)
            return browser, f"channel={channel}"
        except Exception as exc:
            message = str(exc).splitlines()[0]
            errors.append(f"{label} channel: {message}")
            logger.warning("Browser discovery: %s channel unavailable: %s", label, message)

    seen: set[str] = set()
    for label, path in _candidate_executables():
        key = str(path).lower()
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        logger.info("Browser discovery: trying %s executable_path=%s", label, path)
        try:
            browser = playwright.chromium.launch(executable_path=str(path), headless=headless)
            logger.info("Browser discovery: launched %s from %s", label, path)
            return browser, f"executable_path={path}"
        except Exception as exc:
            message = str(exc).splitlines()[0]
            errors.append(f"{label} executable {path}: {message}")
            logger.warning("Browser discovery: executable failed: %s", message)

    detail = " | ".join(errors) if errors else "No Chrome/Edge executable was found."
    raise BrowserUnavailableError(
        "No usable installed Chrome or Edge browser is available; no browser was downloaded. " + detail
    )
