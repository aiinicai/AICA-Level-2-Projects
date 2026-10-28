import unittest
from datetime import datetime, timedelta, timezone
from io import StringIO
from contextlib import redirect_stdout
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import living_ai_book as book


class FeedParsingTests(unittest.TestCase):
    def test_parses_atom_and_cleans_markup(self):
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>A &amp; B update</title>
            <link href="https://example.com/news/1"/>
            <published>2026-10-18T10:00:00Z</published>
            <summary>&lt;p&gt;A useful &lt;b&gt;new&lt;/b&gt; tool.&lt;/p&gt;</summary>
          </entry>
        </feed>"""
        updates = book.parse_feed(
            content,
            "Example",
            "2026-10-18T10:00:00+00:00",
        )
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["title"], "A & B update")
        self.assertEqual(updates[0]["summary"], "A useful new tool.")
        self.assertEqual(updates[0]["published"], "2026-10-18T10:00:00+00:00")

    def test_skips_entries_without_http_links(self):
        content = b"""<rss><channel><item><title>No link</title></item>
        <item><title>Bad link</title><link>javascript:alert(1)</link></item>
        </channel></rss>"""
        self.assertEqual(book.parse_feed(content, "Example", "now"), [])

    def test_rejects_oversized_feed(self):
        with self.assertRaises(ValueError):
            book.parse_feed(b" " * (book.MAX_FEED_BYTES + 1), "Example", "now")


class UpdateStateTests(unittest.TestCase):
    def test_combines_by_id_and_keeps_newest_first(self):
        old = {"id": "same", "title": "old", "published": "2026-01-01"}
        new = {"id": "same", "title": "new", "published": "2026-02-01"}
        latest = {"id": "latest", "title": "latest", "published": "2026-03-01"}
        updates = book.combine_updates([old], [new, latest])
        self.assertEqual([item["id"] for item in updates], ["latest", "same"])
        self.assertEqual(updates[1]["title"], "new")

    def test_refresh_interval(self):
        now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        fresh = {"refreshed_at": (now - timedelta(hours=1)).isoformat()}
        stale = {"refreshed_at": (now - timedelta(hours=9)).isoformat()}
        self.assertFalse(book.is_refresh_due(fresh, now))
        self.assertTrue(book.is_refresh_due(stale, now))
        self.assertTrue(book.is_refresh_due({}, now))


class AuthorPageTests(unittest.TestCase):
    def test_author_page_is_last_in_terminal_book(self):
        output = StringIO()
        with redirect_stdout(output):
            book.print_terminal_book(book.empty_update_state())
        rendered = output.getvalue()
        self.assertIn("Harit Kumar, CA, CFE", rendered)
        self.assertIn(book.AUTHOR_PAGE["profile_url"], rendered)
        self.assertGreater(
            rendered.index(book.AUTHOR_PAGE["title"]),
            rendered.index("Latest AI developments"),
        )

    def test_terminal_book_includes_timeline_milestones_and_sources(self):
        output = StringIO()
        with redirect_stdout(output):
            book.print_terminal_book(book.empty_update_state())
        rendered = output.getvalue()
        self.assertIn("1950: Turing asks a big question", rendered)
        self.assertIn("2012: Neural networks make waves in image contests", rendered)
        self.assertIn("https://doi.org/10.1145/3065386", rendered)


class BrowserBookTests(unittest.TestCase):
    def test_book_has_linked_contents_live_news_and_author_last(self):
        state = book.empty_update_state()
        state["updates"] = [
            {
                "id": "update-1",
                "title": "New model announcement",
                "summary": "A source description.",
                "url": "https://example.com/announcement",
                "source": "Example",
                "published": "2026-10-18T10:00:00+00:00",
                "fetched_at": "2026-10-18T10:00:00+00:00",
            }
        ]
        data = book.build_book_data(state)
        self.assertEqual(data["pages"][-1]["kind"], "author")
        self.assertEqual(data["pages"][-1]["title"], "Harit Kumar, CA, CFE")
        self.assertTrue(any(item["title"] == "News: New model announcement" for item in data["contents"]))
        self.assertTrue(any(item["title"] == "The prompt playground" for item in data["pages"]))
        self.assertEqual(data["newsCount"], 1)
        self.assertTrue(any(item["title"].startswith("New field notes:") for item in data["contents"]))

    def test_timeline_has_source_links_and_cartoon_illustrations(self):
        data = book.build_book_data(book.empty_update_state())
        timeline_pages = [
            page for page in data["pages"] if page["kind"] == "timeline-event"
        ]
        self.assertEqual(len(timeline_pages), len(book.AI_TIMELINE))
        self.assertEqual(
            [page["kicker"] for page in timeline_pages],
            [event["year"] for event in book.AI_TIMELINE],
        )
        self.assertTrue(all(page["links"][0]["url"].startswith("https://") for page in timeline_pages))
        self.assertEqual(timeline_pages[0]["illustration"], "timeline")
        self.assertEqual(data["pages"][0]["illustration"], "reader-robot")
        illustrations = {
            page.get("illustration")
            for page in data["pages"]
            if page.get("illustration")
        }
        self.assertTrue(
            {
                "reader-robot",
                "seedling",
                "timeline",
                "training-examples",
                "word-guess",
                "check-answer",
                "picture-clues",
            }.issubset(illustrations)
        )

    def test_explanatory_cartoons_are_rendered_with_child_friendly_captions(self):
        source = Path(book.__file__).read_text(encoding="utf-8")
        self.assertIn("Examples go in; the computer practises spotting patterns.", source)
        self.assertIn("It predicts a likely next word; it is not looking up a perfect answer.", source)
        self.assertIn("A person checks important answers with a trusted source.", source)
        self.assertIn('"cartoon-caption"', source)

    def test_ai_application_guide_lists_requested_tools_with_official_links(self):
        data = book.build_book_data(book.empty_update_state())
        app_pages = [page for page in data["pages"] if page["kind"] == "applications"]
        app_entries = app_pages[0]["applications"]
        application_toc = [
            item for item in data["contents"]
            if item["title"].startswith("App:")
        ]
        self.assertEqual(len(app_pages), 1)
        self.assertEqual(
            [app["name"] for app in app_entries],
            ["ChatGPT", "Google Gemini", "Claude", "Lovable", "n8n"],
        )
        self.assertTrue(all(app["url"].startswith("https://") for app in app_entries))
        self.assertTrue(all(app["use_when"] for app in app_entries))
        self.assertEqual(application_toc, [])
        self.assertTrue(any(item["title"] == "6. AI applications to explore" for item in data["contents"]))

    def test_ai_and_asi_are_distinguished_without_claiming_asi_exists(self):
        text = " ".join(
            paragraph
            for chapter in book.BOOK_CHAPTERS
            for _, paragraph, *_ in chapter["sections"]
        )
        self.assertIn("artificial intelligence, or AI", text)
        self.assertIn("artificial superintelligence", text)
        self.assertIn("remain hypothetical", text)
        self.assertNotIn("smart intelligence” as a playful", text)

    def test_field_notes_are_added_to_related_existing_chapter(self):
        update = {
            "id": "update-1",
            "title": "A new language model",
            "summary": "A research update about chatbot reasoning.",
            "url": "https://example.com/announcement",
            "source": "Example",
            "published": "",
            "fetched_at": "2026-10-18T10:00:00+00:00",
        }
        self.assertEqual(
            book.related_chapter(update),
            "3. How does a language model write?",
        )
        page = next(
            page
            for page in book.build_book_data({"updates": [update]})["pages"]
            if page["kind"] == "field-notes"
        )
        self.assertIn("1 recent announcement", page["paragraphs"][0])
        self.assertEqual(page["links"][0]["url"], update["url"])

    def test_export_writes_a_standalone_book_edition(self):
        state = book.empty_update_state()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "book-data.json"
            with (
                patch.object(book, "PWA_DIR", Path(directory)),
                patch.object(book, "PWA_DATA_FILE", destination),
            ):
                self.assertEqual(book.export_pwa_data(state), destination)
            exported = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(exported["pages"][-1]["kind"], "author")
        self.assertEqual(exported["newsCount"], 0)

    def test_browser_document_escapes_feed_text_and_has_keyboard_controls(self):
        state = book.empty_update_state()
        state["updates"] = [
            {
                "id": "unsafe-title",
                "title": "<script>bad()</script>",
                "summary": "A sourced summary.",
                "url": "https://example.com/announcement",
                "source": "Example",
                "published": "",
                "fetched_at": "2026-10-18T10:00:00+00:00",
            }
        ]
        document = book.render_browser_document(state)
        self.assertNotIn("<script>bad()</script>", document)
        self.assertIn(r"\u003cscript\u003ebad()", document)
        self.assertIn('event.key === "ArrowRight"', document)
        self.assertIn('event.key === "ArrowLeft"', document)
        self.assertIn('id="contents-button"', document)


if __name__ == "__main__":
    unittest.main()
