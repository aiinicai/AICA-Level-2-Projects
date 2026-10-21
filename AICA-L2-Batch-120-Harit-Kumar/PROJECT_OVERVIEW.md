# Project Overview

## Title

**The Living AI Book: an interactive, updateable guide for young readers**

## Purpose

AI tools and announcements change quickly. This project introduces core AI ideas in plain language for readers aged 10–12 and provides a source-linked feed shelf for selected recent announcements.

## Audience and problem

The intended readers are curious children aged 10–12, supported by parents and educators. The book aims to make AI approachable while teaching that systems have limitations, results need checking, and people are responsible for how tools are used.

## What I built

The project has two reading options:

1. **Python reader:** a local browser book served by Python's standard-library HTTP server. It refreshes public feeds and builds a book edition.
2. **Static PWA:** an interactive book made with HTML, CSS, and JavaScript. A web manifest describes installation; a service worker caches the application shell and most recently loaded edition for offline reading.

The content includes a selected, sourced AI timeline; original cartoons explaining examples, word prediction, picture clues, and fact-checking; safety guidance; a prompt preview; and one applications chapter for ChatGPT, Gemini, Claude, Lovable, and n8n. Each app includes a short note about when it may be useful.

## Tools and libraries used

- Visual Studio Code for editing, running, and organizing files.
- Python 3 standard library for HTTP serving, RSS/XML parsing, URL requests, JSON data, and unit tests.
- HTML, CSS, and JavaScript for the browser/PWA interface and navigation.
- Web App Manifest and Service Worker APIs for installation support and caching.
- Git and GitHub for version control, fork-based submission, commits, and pull requests.
- GitHub Actions and GitHub Pages for optional scheduled data refresh and HTTPS deployment, if permissions and repository settings allow it.

There is no third-party Python dependency and no JavaScript framework dependency.

## Architecture / flow

Authored chapters and selected public feed entries are assembled by the Python program into structured book data. The local reader can serve the interface directly; the generated data is also consumed by the static PWA. If configured, GitHub Actions can refresh the edition and publish the PWA folder to GitHub Pages.

See [FLOWCHART.svg](./FLOWCHART.svg) for the visual process diagram.

## Responsible use and limitations

- Publisher-provided descriptions and announcements are not independent evidence or fact-checks.
- Topic association is a simple keyword match, not an AI-written summary or analysis.
- The prompt playground only builds a local preview and sends nothing to an AI service.
- Important information should be checked against reliable sources with a trusted adult.
- The PWA can show the cached edition offline. Phones may pause background tasks, so refresh while the app is closed is not guaranteed.
- Product capabilities and access policies can change; official links are provided for checking current information.

## Validation

Run `py -m unittest -v test_living_ai_book.py` from this folder. The tests cover feed parsing, generated book structure, timeline and applications content, author page, and exports.

## Deployment and submission status

The user-provided live PWA is [https://haritkumarca-web.github.io/AiBook/](https://haritkumarca-web.github.io/AiBook/). The site responds with the book's welcome page. The included workflow and source are the capstone package; publishing updates from this package still depends on the repository's GitHub Pages and Actions settings.
