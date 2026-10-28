from __future__ import annotations

import argparse
import concurrent.futures
import email.utils
import hashlib
import html
from html.parser import HTMLParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any
import webbrowser
from urllib.parse import unquote, urlsplit


APP_TITLE = "The Living AI Book"
REFRESH_INTERVAL = timedelta(hours=8)
MAX_UPDATES = 120
MAX_FEED_BYTES = 1_500_000
MAX_ITEMS_PER_FEED = 12
UPDATE_FILE = Path(__file__).resolve().with_name("ai_updates.json")
PWA_DIR = Path(__file__).resolve().parent / "pwa"
PWA_DATA_FILE = PWA_DIR / "book-data.json"

FEEDS = (
    {
        "name": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
        "news_page": "https://openai.com/news/",
    },
    {
        "name": "Google AI",
        "url": "https://blog.google/technology/ai/rss/",
        "news_page": "https://blog.google/technology/ai/",
    },
    {
        "name": "Hugging Face",
        "url": "https://huggingface.co/blog/feed.xml",
        "news_page": "https://huggingface.co/blog",
    },
)

AI_TIMELINE = (
    {
        "year": "1950",
        "title": "Turing asks a big question",
        "text": (
            "Mathematician Alan Turing described an “imitation game” to explore how we might "
            "judge a machine by its conversation. It started a lasting discussion about machines "
            "and thinking."
        ),
        "source": "Turing's paper, Computing Machinery and Intelligence",
        "url": "https://doi.org/10.1093/mind/LIX.236.433",
    },
    {
        "year": "1956",
        "title": "AI becomes a research field",
        "text": (
            "At a summer workshop at Dartmouth College, researchers helped establish artificial "
            "intelligence as a field of study. The name “artificial intelligence” was used in "
            "the workshop proposal."
        ),
        "source": "Dartmouth: The research conference where AI began",
        "url": "https://home.dartmouth.edu/about/artificial-intelligence-ai-coined-dartmouth",
    },
    {
        "year": "1966",
        "title": "ELIZA chats using written rules",
        "text": (
            "Joseph Weizenbaum described ELIZA, an early computer program that replied to typed "
            "messages using patterns and rules. Its replies could feel conversational, even though "
            "the program did not understand like a person."
        ),
        "source": "Weizenbaum's paper on ELIZA (ACM Digital Library)",
        "url": "https://doi.org/10.1145/365153.365168",
    },
    {
        "year": "1997",
        "title": "Deep Blue wins a chess match",
        "text": (
            "IBM's Deep Blue beat world chess champion Garry Kasparov in a six-game match. "
            "It was a remarkable chess achievement—but Deep Blue was designed to play chess, "
            "not to do every kind of human thinking."
        ),
        "source": "IBM: Deep Blue",
        "url": "https://www.ibm.com/history/deep-blue",
    },
    {
        "year": "2012",
        "title": "Neural networks make waves in image contests",
        "text": (
            "AlexNet, a deep neural network, achieved a major result in the ImageNet image-recognition "
            "challenge. It helped draw attention to what neural networks could learn from many "
            "labelled examples."
        ),
        "source": "Krizhevsky et al., 2012 paper (ACM reprint): ImageNet Classification with Deep Convolutional Neural Networks",
        "url": "https://doi.org/10.1145/3065386",
    },
    {
        "year": "2017",
        "title": "The Transformer idea is published",
        "text": (
            "Researchers introduced the Transformer, a new way for computers to work with "
            "relationships between pieces of language. It became an important building block "
            "for many later language models."
        ),
        "source": "The original Transformer research paper",
        "url": "https://arxiv.org/abs/1706.03762",
    },
    {
        "year": "2022",
        "title": "ChatGPT opens to the public",
        "text": (
            "OpenAI introduced ChatGPT as a research preview in November. Many people could "
            "try a conversational AI tool directly, helping make chat with language models "
            "a familiar experience."
        ),
        "source": "OpenAI: Introducing ChatGPT",
        "url": "https://openai.com/index/chatgpt/",
    },
    {
        "year": "2024",
        "title": "Machine-learning pioneers receive a Nobel Prize",
        "text": (
            "The Nobel Prize in Physics recognized John Hopfield and Geoffrey Hinton for "
            "discoveries and inventions that helped make machine learning with artificial "
            "neural networks possible."
        ),
        "source": "Nobel Prize: They used physics to find patterns in information",
        "url": "https://www.nobelprize.org/prizes/physics/2024/popular-information/",
    },
)

AI_APPLICATIONS = (
    {
        "name": "ChatGPT",
        "category": "AI assistant",
        "description": (
            "A chat-based helper for questions, writing ideas, explanations, and other tasks. "
            "It can make mistakes, so check important answers."
        ),
        "use_when": "You want to ask questions, understand a topic, or brainstorm a first draft.",
        "url": "https://chatgpt.com/",
    },
    {
        "name": "Google Gemini",
        "category": "AI assistant",
        "description": (
            "Google's AI assistant can help people explore questions and work with different "
            "kinds of information. Available features depend on the account, device, and region."
        ),
        "use_when": "You want an AI assistant for questions and help exploring information.",
        "url": "https://gemini.google.com/",
    },
    {
        "name": "Claude",
        "category": "AI assistant",
        "description": (
            "An AI assistant from Anthropic that can help with questions, writing, and working "
            "with files. Treat its answers as suggestions to review, not guaranteed facts."
        ),
        "use_when": "You want help discussing ideas, drafting text, or reviewing documents.",
        "url": "https://claude.ai/",
    },
    {
        "name": "Lovable",
        "category": "AI app-building tool",
        "description": (
            "A tool for creating website and app prototypes from written instructions. "
            "A real app still needs people to test it, protect user information, and check its code."
        ),
        "use_when": "You want to turn an app idea into a first website or app prototype.",
        "url": "https://lovable.dev/",
    },
    {
        "name": "n8n",
        "category": "Workflow automation",
        "description": (
            "A tool for connecting apps and services into automated workflows. It is more like "
            "building a set of linked steps than chatting with a general AI assistant."
        ),
        "use_when": "You want different apps to pass information or carry out repeatable steps automatically.",
        "url": "https://n8n.io/",
    },
)

AUTHOR_PAGE = {
    "title": "About the author",
    "name": "Harit Kumar, CA, CFE",
    "bio": (
        "Harit Kumar is a Chartered Accountant (CA) and Certified Fraud Examiner (CFE). "
        "He created this book to help young readers explore artificial intelligence with "
        "clear explanations, curiosity, and safe habits."
    ),
    "profile_url": "https://www.linkedin.com/in/harit-kumar-ca-cfe-45961617/",
}

BROWSER_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f4efe5">
<title>The Living AI Book</title>
<style>
:root {
  color-scheme: light;
  --ink: #25372f;
  --muted: #72786d;
  --green: #325b49;
  --green-deep: #203d32;
  --gold: #bb9254;
  --paper: #fffdf7;
  --paper-edge: #ebe2d1;
  --desk: #eee7db;
  font-family: "Segoe UI", "Trebuchet MS", system-ui, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background:
    radial-gradient(ellipse at 50% 0%, #fbf9f2 0, transparent 49%),
    linear-gradient(140deg, #f6f1e8, var(--desk));
}
button, a { font: inherit; }
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible {
  outline: 3px solid #bc8d48;
  outline-offset: 3px;
}
.shell { max-width: 1260px; padding: 24px 30px 20px; margin: 0 auto; }
.topbar, .toolbar, .book-footer, .spread-nav, .progress-row {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
}
.topbar { margin-bottom: 21px; }
.brand { display: flex; gap: 13px; align-items: center; }
.brand-mark {
  width: 43px; height: 43px; display: grid; place-items: center;
  border-radius: 13px; color: #f9f4e8; background: var(--green);
  box-shadow: 0 4px 10px #203d3224;
}
.brand-mark svg { width: 23px; height: 23px; }
.brand-title { font-family: Georgia, serif; font-size: 19px; letter-spacing: -.3px; }
.brand-subtitle { display: block; margin-top: 2px; color: var(--muted); font-size: 12px; }
.top-actions { display: flex; align-items: center; gap: 10px; }
.status { color: var(--muted); font-size: 12px; }
.status-dot { display: inline-block; width: 7px; height: 7px; margin-right: 6px;
  border-radius: 50%; background: #6c9679; }
.button {
  min-height: 40px; padding: 9px 14px; border: 1px solid #d9d0c0;
  border-radius: 9px; color: var(--ink); background: #fffdf8; cursor: pointer;
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
}
.button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px #342b1c14; }
.button:disabled { opacity: .42; cursor: default; }
.button-primary { color: white; background: var(--green); border-color: var(--green); }
.button-primary:hover:not(:disabled) { background: var(--green-deep); }
.button-icon { display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
.reader-heading { text-align: center; margin: 8px 0 21px; }
.reader-heading h1 { margin: 0; font: 500 clamp(24px, 3vw, 34px)/1.2 Georgia, serif; }
.reader-heading p { margin: 8px 0 0; color: var(--muted); font-size: 14px; }
.book-wrap { position: relative; max-width: 1090px; margin: 0 auto; }
.book {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  min-height: 500px; overflow: hidden; border: 1px solid #d9cfbd; border-radius: 9px;
  background: var(--paper); box-shadow: 0 26px 55px #42362924, 0 4px 11px #42362914;
  perspective: 1800px;
}
.page {
  position: relative; min-width: 0; min-height: 500px; padding: clamp(27px, 5vw, 62px);
  background:
    linear-gradient(90deg, #f6f1e8aa, transparent 5%, transparent 96%, #eee8dc55),
    var(--paper);
}
.left-page { border-right: 1px solid #e5ddcf; box-shadow: inset -13px 0 22px -24px #3b3228; }
.right-page { box-shadow: inset 13px 0 22px -24px #3b3228; }
.right-page::before, .left-page::before {
  position: absolute; top: 0; bottom: 0; width: 13px; content: ""; pointer-events: none;
}
.left-page::before { right: 0; background: linear-gradient(90deg, transparent, #8171580a); }
.right-page::before { left: 0; background: linear-gradient(90deg, #8171580a, transparent); }
.page-inner { min-height: 405px; display: flex; flex-direction: column; }
.book-cartoon { display: flex; min-height: 88px; align-items: center; justify-content: center; margin: 0 auto 8px; }
.book-cartoon svg { display: block; width: 126px; height: 88px; overflow: visible; }
.book-cartoon figcaption { color: #667064; text-align: center; font: 12px/1.4 "Segoe UI", sans-serif; }
.cartoon-training-examples, .cartoon-word-guess, .cartoon-check-answer, .cartoon-picture-clues { width: 100%; min-height: 0; flex-direction: column; gap: 3px; margin: 7px auto 12px; }
.cartoon-training-examples svg, .cartoon-word-guess svg, .cartoon-check-answer svg, .cartoon-picture-clues svg { width: min(100%, 340px); height: auto; }
.cartoon-reader-robot { min-height: 142px; margin-bottom: 15px; }
.cartoon-reader-robot svg { width: min(190px, 72%); height: 142px; }
.cartoon-seedling { min-height: 88px; justify-content: flex-start; margin-left: 0; }
.cartoon-seedling svg { width: 112px; height: 88px; }
.page-kicker { color: #947344; text-transform: uppercase; letter-spacing: 2px;
  font-size: 10px; font-weight: 700; margin: 0 0 13px; }
.page h2 { margin: 0 0 21px; font: 500 clamp(23px, 2.5vw, 32px)/1.17 Georgia, serif; letter-spacing: -.4px; }
.page p { margin: 0 0 17px; color: #4c564e; font: 16px/1.8 Georgia, serif; }
.page .page-callout {
  margin-top: auto; padding: 14px 16px; border-left: 3px solid var(--gold);
  border-radius: 0 8px 8px 0; background: #f5f0e6; color: #46564b;
  font: 14px/1.65 "Segoe UI", sans-serif;
}
.page-label { margin-top: auto; color: #9a958b; font: italic 13px Georgia, serif; }
.page-links { display: grid; gap: 11px; margin: 5px 0 18px; }
.page-link {
  display: inline-flex; align-items: flex-start; gap: 8px; color: #315f4b;
  line-height: 1.45; text-decoration-thickness: 1px; text-underline-offset: 3px;
}
.page-link::before { content: "↗"; font-size: 12px; text-decoration: none; }
.page-link:hover { color: #8a642c; }
.page-list { padding-left: 20px; color: #4c564e; font: 15px/1.8 Georgia, serif; }
.cover-page {
  justify-content: center; text-align: center; border: 1px solid #d0ba8b; border-radius: 4px;
  background:
    linear-gradient(135deg, #ffffff08, transparent 48%, #172c2340),
    #315643;
  color: #f8f1e2; box-shadow: inset 0 0 0 9px #315643, inset 0 0 0 10px #c3a66d99;
}
.cover-page .book-cartoon { flex: 0 0 auto; }
.cover-page .page-kicker { color: #ddc998; letter-spacing: 3px; }
.cover-page h2 { margin: 0 auto 16px; max-width: 340px; font-size: clamp(34px, 5vw, 55px); }
.cover-page p { color: #e8e2d3; font: 16px/1.7 Georgia, serif; }
.cover-rule { width: 58px; height: 1px; margin: 21px auto; background: #d5bd82; }
.cover-author { margin-top: 34px; color: #d9cba8; font-size: 12px; letter-spacing: 1px; }
.timeline-page .page-kicker { display: inline-flex; align-self: flex-start; padding: 5px 10px; border-radius: 99px; color: #315643; background: #f2ead6; font-size: 13px; letter-spacing: .6px; }
.timeline-page .book-cartoon { min-height: 100px; margin: 0 auto 12px; }
.timeline-page .book-cartoon svg { width: 150px; height: 100px; }
.application-page .page-kicker { display: inline-flex; align-self: flex-start; padding: 6px 10px; border: 1px solid #d8c9a8; border-radius: 99px; color: #536b55; background: #f5f1e7; letter-spacing: .7px; }
.application-page .page-links { margin-top: 15px; padding: 13px; border: 1px solid #e3d8c5; border-radius: 9px; background: #faf7ef; }
.application-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; margin: 12px 0; }
.application-entry { padding: 10px 11px; border: 1px solid #e3d8c5; border-radius: 9px; background: #faf8f1; }
.application-entry h3 { margin: 0 0 5px; font: 600 15px Georgia, serif; }
.application-entry .page-link { font-weight: 700; }
.application-entry p { margin: 0 0 5px; font: 12px/1.45 "Segoe UI", sans-serif; }
.application-entry .application-use { margin: 0; color: #315643; font-weight: 600; }
.blank-page { display: grid; place-items: center; color: #c5bba9; }
.blank-page span { font: italic 14px Georgia, serif; }
.table-of-contents { display: grid; gap: 8px; margin: 6px 0; }
.toc-link {
  display: flex; align-items: baseline; gap: 8px; width: 100%; padding: 8px 0;
  border: 0; border-bottom: 1px dotted #d4c9b6; text-align: left; color: #315f4b;
  background: none; cursor: pointer;
}
.toc-link:hover { color: #8a642c; }
.toc-number { min-width: 25px; color: #9a7847; font-size: 12px; font-variant-numeric: tabular-nums; }
.activity-box { display: grid; gap: 12px; padding: 17px; margin-top: 7px;
  border: 1px solid #e3d8c5; border-radius: 10px; background: #faf7ef; }
.activity-box label { color: #566257; font-size: 12px; font-weight: 600; }
.activity-box input, .activity-box select {
  width: 100%; min-height: 40px; padding: 8px 10px; border: 1px solid #d9d0c0;
  border-radius: 7px; background: white; color: var(--ink);
}
.prompt-preview {
  min-height: 73px; margin: 0 !important; padding: 12px; border-radius: 7px;
  background: #eef0e9; color: #3d5045 !important; white-space: pre-wrap;
  font: 13px/1.55 ui-monospace, Consolas, monospace !important;
}
.book-footer { max-width: 1090px; margin: 13px auto 0; }
.page-number { color: var(--muted); font: 13px Georgia, serif; min-width: 100px; text-align: center; }
.progress-row { max-width: 1090px; margin: 19px auto 0; gap: 13px; }
.progress-track { height: 3px; flex: 1; overflow: hidden; border-radius: 99px; background: #dcd4c6; }
.progress-value { height: 100%; width: 0; border-radius: inherit; background: var(--gold); transition: width .35s ease; }
.keyboard-hint { color: var(--muted); font-size: 11px; }
.bottom-note { padding: 18px 8px 3px; color: #8a897f; text-align: center; font-size: 11px; line-height: 1.6; }
.error-note { max-width: 1090px; margin: 12px auto; color: #815229; font-size: 12px; }
.error-note:empty { display: none; }
dialog {
  width: min(470px, calc(100% - 28px)); max-height: 78vh; padding: 25px;
  border: 1px solid #d9cfbd; border-radius: 13px; color: var(--ink);
  background: #fffdf7; box-shadow: 0 20px 60px #1f2e2440;
}
dialog::backdrop { background: #20272077; backdrop-filter: blur(2px); }
.dialog-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.dialog-head h2 { margin: 0 0 14px; font: 500 25px Georgia, serif; }
.dialog-head .page-kicker { margin: 0 0 8px; }
.book.turn-next .right-page { animation: turn-next .32s ease; }
.book.turn-previous .left-page { animation: turn-previous .32s ease; }
@keyframes turn-next { 0% { transform: rotateY(0); } 45% { transform: rotateY(-4deg); } 100% { transform: rotateY(0); } }
@keyframes turn-previous { 0% { transform: rotateY(0); } 45% { transform: rotateY(4deg); } 100% { transform: rotateY(0); } }
@media (max-width: 720px) {
  .shell { padding: 16px 12px; }
  .topbar { align-items: flex-start; }
  .brand-subtitle { max-width: 190px; }
  .status { display: none; }
  .book { display: block; min-height: 430px; }
  .page { display: none; min-height: 430px; padding: 30px 27px; }
  .page.active-page { display: block; }
  .page-inner { min-height: 366px; }
  .application-list { grid-template-columns: 1fr; }
  .book-cartoon { min-height: 76px; }
  .book-cartoon svg { height: 76px; }
  .cartoon-reader-robot { min-height: 126px; }
  .cartoon-reader-robot svg { height: 126px; }
  .cartoon-seedling { min-height: 76px; }
  .cartoon-training-examples svg, .cartoon-word-guess svg, .cartoon-check-answer svg, .cartoon-picture-clues svg { height: auto; }
  .timeline-page .book-cartoon { min-height: 88px; }
  .timeline-page .book-cartoon svg { height: 88px; }
  .left-page { border: 0; }
  .book-footer .keyboard-hint { display: none; }
  .reader-heading { margin-bottom: 15px; }
  .button { min-height: 38px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
</style>
</head>
<body>
<main class="shell">
  <header class="topbar">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M3.5 5.7c3.2-.9 5.9-.2 8.5 1.7v12c-2.6-1.9-5.3-2.6-8.5-1.7z"/>
          <path d="M20.5 5.7c-3.2-.9-5.9-.2-8.5 1.7v12c2.6-1.9 5.3-2.6 8.5-1.7z"/>
        </svg>
      </div>
      <div><span class="brand-title">The Living AI Book</span>
        <span class="brand-subtitle">A curious reader's guide to artificial intelligence</span></div>
    </div>
    <div class="top-actions">
      <span id="news-status" class="status"><span class="status-dot"></span>News shelf is ready</span>
      <button id="refresh-button" class="button button-icon" type="button" aria-label="Check for AI news">
        <span aria-hidden="true">↻</span> Update news
      </button>
    </div>
  </header>
  <section class="reader-heading">
    <h1 id="reader-title">A book that grows with discovery</h1>
    <p id="reader-subtitle">For curious readers ages 10–12 · take your time, turn a page, follow a question.</p>
  </section>
  <div class="book-wrap">
    <section id="book" class="book" aria-label="Open book">
      <article id="left-page" class="page left-page" aria-label="Left page"></article>
      <article id="right-page" class="page right-page" aria-label="Right page"></article>
    </section>
  </div>
  <div id="refresh-errors" class="error-note" role="status" aria-live="polite"></div>
  <nav class="book-footer" aria-label="Book navigation">
    <button id="previous-button" class="button button-icon" type="button" aria-label="Turn to the previous spread">
      <span aria-hidden="true">←</span><span class="previous-label">Previous</span>
    </button>
    <span id="page-number" class="page-number" aria-live="polite"></span>
    <span class="keyboard-hint">Use ← and → arrow keys to turn pages</span>
    <button id="contents-button" class="button" type="button" aria-haspopup="dialog">Contents</button>
    <button id="next-button" class="button button-primary button-icon" type="button" aria-label="Turn to the next spread">
      <span class="next-label">Next</span><span aria-hidden="true">→</span>
    </button>
  </nav>
  <div class="progress-row" aria-label="Reading progress">
    <span class="keyboard-hint">READING PROGRESS</span>
    <div class="progress-track"><div id="progress-value" class="progress-value"></div></div>
    <span id="progress-percent" class="keyboard-hint"></span>
  </div>
  <p class="bottom-note">AI can be helpful and still make mistakes. Check important information with a trusted adult.<br>
    News titles and summaries are linked to their original sources and are not independent fact-checks.</p>
</main>
<dialog id="contents-dialog" aria-labelledby="contents-title">
  <div class="dialog-head"><div><p class="page-kicker">The living AI book</p><h2 id="contents-title">Choose a chapter</h2></div>
    <button class="button" id="close-contents" type="button" aria-label="Close contents">✕</button></div>
  <div id="contents-list" class="table-of-contents"></div>
</dialog>
<script id="book-data" type="application/json">__BOOK_DATA__</script>
<script>
const bookData = JSON.parse(document.getElementById("book-data").textContent);
let pages = bookData.pages;
const leftPage = document.getElementById("left-page");
const rightPage = document.getElementById("right-page");
const bookEl = document.getElementById("book");
const previousButton = document.getElementById("previous-button");
const nextButton = document.getElementById("next-button");
const dialog = document.getElementById("contents-dialog");
let currentPageIndex = 0;
let turning = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function safeLink(link) {
  try {
    const parsed = new URL(link.url);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") return null;
  } catch (_) { return null; }
  const anchor = element("a", "page-link", link.label);
  anchor.href = link.url;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  return anchor;
}

const BOOK_ILLUSTRATIONS = Object.freeze({
  "reader-robot": {
    svg: `<svg viewBox="0 0 180 132" aria-hidden="true"><path d="M30 111h120" stroke="#d8c58f" stroke-width="3" stroke-linecap="round"/><path d="M69 36V25m42 11V25" stroke="#f0d38a" stroke-width="4" stroke-linecap="round"/><circle cx="69" cy="22" r="5" fill="#f0d38a"/><circle cx="111" cy="22" r="5" fill="#f0d38a"/><rect x="50" y="34" width="80" height="63" rx="20" fill="#f3dca4" stroke="#263f34" stroke-width="4"/><path d="M66 60h12m24 0h12" stroke="#315643" stroke-width="7" stroke-linecap="round"/><path d="M76 77q14 13 28 0" fill="none" stroke="#b56e51" stroke-width="4" stroke-linecap="round"/><path d="M61 99 43 111m76-12 18 12" stroke="#f3dca4" stroke-width="8" stroke-linecap="round"/><path d="M42 72 31 79m107-7 11 7" stroke="#f3dca4" stroke-width="7" stroke-linecap="round"/><path d="M49 101q-16-10-26-2v17h30m78-15q16-10 26-2v17h-30" fill="#fbf3dd" stroke="#c5a768" stroke-width="3" stroke-linejoin="round"/><path d="M90 103v13m-27-13q13 10 27 10m27-10q-13 10-27 10" fill="none" stroke="#bd985d" stroke-width="2"/></svg>`,
    caption: "A friendly guide for curious minds."
  },
  "seedling": {
    svg: `<svg viewBox="0 0 120 100" aria-hidden="true"><path d="M60 79V39" stroke="#315643" stroke-width="5" stroke-linecap="round"/><path d="M59 54C37 55 28 43 31 28c18 0 30 7 28 26Zm3-10c2-19 15-29 32-25-2 17-12 27-32 25Z" fill="#9cbe83" stroke="#315643" stroke-width="3" stroke-linejoin="round"/><path d="M39 78h42l-6 16H45Z" fill="#d89c70" stroke="#8c573d" stroke-width="3" stroke-linejoin="round"/><path d="M36 77h48" stroke="#8c573d" stroke-width="4" stroke-linecap="round"/><circle cx="91" cy="21" r="8" fill="#f0d38a"/><path d="m90 8 1-4m12 17 4 1M81 16l-4-3" stroke="#bd985d" stroke-width="2" stroke-linecap="round"/></svg>`,
    caption: "Small helpful tools can grow into big ideas."
  },
  "timeline": {
    svg: `<svg viewBox="0 0 150 100" aria-hidden="true"><path d="M20 72h110" stroke="#c8b17a" stroke-width="4" stroke-linecap="round"/><circle cx="31" cy="72" r="7" fill="#d9946e"/><circle cx="75" cy="72" r="7" fill="#88a776"/><circle cx="119" cy="72" r="7" fill="#7893a5"/><path d="M75 62V34" stroke="#315643" stroke-width="3"/><circle cx="75" cy="26" r="19" fill="#f4e4b9" stroke="#315643" stroke-width="3"/><path d="M75 14v12l9 5" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="m29 57 3-10 3 10m40-2 3-10 3 10m40 2 3-10 3 10" fill="#fffdf7" stroke="#bd985d" stroke-width="2" stroke-linejoin="round"/><path d="M27 88h8m36 0h8m36 0h8" stroke="#c8b17a" stroke-width="2" stroke-linecap="round"/></svg>`,
    caption: "AI has many milestones, not just one big invention."
  },
  "training-examples": {
    svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="10" y="16" width="94" height="88" rx="14" fill="#f8f0dc" stroke="#cdb782" stroke-width="2"/><circle cx="39" cy="50" r="16" fill="#df8063"/><path d="M39 32q-2-9 7-9m-7 9q-9-8-14-1" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><circle cx="76" cy="50" r="16" fill="#efbd65"/><path d="M76 31q4-8 10-5" fill="none" stroke="#75945f" stroke-width="3" stroke-linecap="round"/><text x="57" y="88" text-anchor="middle" font-size="12" fill="#45564a">labelled pictures</text><path d="M111 60h29m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="149" y="22" width="66" height="76" rx="19" fill="#dce8dc" stroke="#315643" stroke-width="3"/><circle cx="172" cy="51" r="4" fill="#315643"/><circle cx="192" cy="51" r="4" fill="#315643"/><path d="M171 68q10 8 21 0" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><text x="182" y="91" text-anchor="middle" font-size="11" fill="#315643">practice</text><path d="M222 60h29m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="260" y="23" width="70" height="76" rx="13" fill="#fff9ec" stroke="#cdb782" stroke-width="2"/><circle cx="280" cy="51" r="12" fill="#df8063"/><circle cx="310" cy="51" r="12" fill="#efbd65"/><text x="295" y="88" text-anchor="middle" font-size="12" fill="#45564a">new guesses</text></svg>`,
    caption: "Examples go in; the computer practises spotting patterns."
  },
  "word-guess": {
    svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="8" y="35" width="105" height="52" rx="12" fill="#f8f0dc" stroke="#cdb782" stroke-width="2"/><text x="60" y="57" text-anchor="middle" font-size="12" fill="#45564a">“The dog wagged</text><text x="60" y="75" text-anchor="middle" font-size="12" fill="#45564a">its…”</text><path d="M120 61h24m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="150" y="29" width="68" height="64" rx="19" fill="#dce8dc" stroke="#315643" stroke-width="3"/><circle cx="173" cy="53" r="4" fill="#315643"/><circle cx="195" cy="53" r="4" fill="#315643"/><path d="M171 69q12 7 24 0" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><path d="M224 61h24m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="255" y="35" width="77" height="52" rx="12" fill="#e9f0e5" stroke="#91ad7b" stroke-width="2"/><text x="293" y="67" text-anchor="middle" font-size="16" font-weight="700" fill="#315643">“tail”</text><text x="184" y="112" text-anchor="middle" font-size="11" fill="#667064">guesses a likely next piece</text></svg>`,
    caption: "It predicts a likely next word; it is not looking up a perfect answer."
  },
  "check-answer": {
    svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="10" y="29" width="102" height="68" rx="14" fill="#dce8dc" stroke="#315643" stroke-width="2"/><circle cx="42" cy="53" r="4" fill="#315643"/><circle cx="78" cy="53" r="4" fill="#315643"/><path d="M42 68q18 10 36 0" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><path d="M62 22v-8m-17 11-5-7m39 7 5-7" stroke="#bd985d" stroke-width="3" stroke-linecap="round"/><text x="61" y="88" text-anchor="middle" font-size="11" fill="#45564a">AI suggests</text><path d="M120 62h25m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="188" cy="49" r="18" fill="#e7b18c" stroke="#845b49" stroke-width="2"/><path d="M158 103q3-31 30-31t30 31" fill="#7893a5" stroke="#496676" stroke-width="2"/><path d="M211 56h25m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="246" y="26" width="82" height="77" rx="5" fill="#fff9ec" stroke="#cdb782" stroke-width="2"/><path d="M260 44h50m-50 13h43m-43 13h50m-50 13h36" stroke="#b8aa8e" stroke-width="3" stroke-linecap="round"/><text x="287" y="117" text-anchor="middle" font-size="11" fill="#45564a">person checks a book</text></svg>`,
    caption: "A person checks important answers with a trusted source."
  },
  "picture-clues": {
    svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="12" y="24" width="94" height="78" rx="12" fill="#f6f0df" stroke="#cdb782" stroke-width="2"/><path d="m31 54 8-18 17 12m18 6 16-18 8 18" fill="#e7b18c" stroke="#845b49" stroke-width="3" stroke-linejoin="round"/><circle cx="57" cy="70" r="24" fill="#e7b18c" stroke="#845b49" stroke-width="3"/><circle cx="49" cy="69" r="3" fill="#263f34"/><circle cx="65" cy="69" r="3" fill="#263f34"/><path d="M53 80q4 4 8 0" fill="none" stroke="#845b49" stroke-width="2"/><path d="M119 62h30m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="187" cy="52" r="23" fill="#dce8dc" stroke="#315643" stroke-width="3"/><path d="M204 69 220 86" stroke="#315643" stroke-width="6" stroke-linecap="round"/><circle cx="181" cy="48" r="4" fill="#315643"/><circle cx="194" cy="48" r="4" fill="#315643"/><path d="M179 60q8 6 16 0" fill="none" stroke="#315643" stroke-width="2"/><text x="274" y="48" text-anchor="middle" font-size="12" fill="#45564a">pointy ears?</text><text x="274" y="69" text-anchor="middle" font-size="12" fill="#45564a">whiskers?</text><text x="274" y="95" text-anchor="middle" font-size="12" font-weight="700" fill="#315643">maybe a cat!</text></svg>`,
    caption: "The app looks for clues—ears and whiskers—but can still be fooled."
  }
});

function renderIllustration(container, illustration) {
  const drawing = BOOK_ILLUSTRATIONS[illustration];
  if (!drawing) return;
  const wrapper = element("figure", `book-cartoon cartoon-${illustration}`);
  wrapper.innerHTML = drawing.svg;
  wrapper.append(element("figcaption", "cartoon-caption", drawing.caption));
  container.append(wrapper);
}

function renderPage(container, page, pageIndex, isMobileActive) {
  container.replaceChildren();
  container.classList.toggle("active-page", isMobileActive);
  container.setAttribute("aria-hidden", String(!isMobileActive && window.innerWidth <= 720));
  if (!page) {
    container.classList.add("blank-page");
    container.append(element("span", "", "The Living AI Book"));
    return;
  }
  container.classList.remove("blank-page");
  if (page.kind === "cover") container.classList.add("cover-page");
  else container.classList.remove("cover-page");
  container.classList.toggle("timeline-page", page.kind === "timeline-event");
  container.classList.toggle("application-page", page.kind === "applications");

  const inner = element("div", "page-inner");
  if (page.kicker) inner.append(element("div", "page-kicker", page.kicker));
  if (page.title) inner.append(element("h2", "", page.title));
  for (const paragraph of (page.paragraphs || [])) inner.append(element("p", "", paragraph));
  if (page.illustration) renderIllustration(inner, page.illustration);

  if (page.kind === "contents") {
    const toc = element("div", "table-of-contents");
    for (const item of bookData.contents) {
      const button = element("button", "toc-link");
      button.type = "button";
      button.append(element("span", "toc-number", String(item.number).padStart(2, "0")));
      button.append(element("span", "", item.title));
      button.addEventListener("click", () => { goToPage(item.page); dialog.close(); });
      toc.append(button);
    }
    inner.append(toc);
  }

  if (page.kind === "applications" && page.applications && page.applications.length) {
    const list = element("div", "application-list");
    for (const application of page.applications) {
      const entry = element("section", "application-entry");
      const heading = element("h3");
      const anchor = safeLink({ label: application.name, url: application.url });
      if (anchor) heading.append(anchor);
      entry.append(heading);
      entry.append(element("p", "application-description", application.description));
      entry.append(element("p", "application-use", `Use it when: ${application.use_when}`));
      list.append(entry);
    }
    inner.append(list);
  }

  if (page.kind === "prompt-builder") {
    const box = element("div", "activity-box");
    const goalLabel = element("label", "", "What would you like help with?");
    const goal = element("input");
    goal.maxLength = 180;
    goal.placeholder = "For example: explain how rainbows form";
    goalLabel.append(goal);
    const styleLabel = element("label", "", "What kind of answer would help?");
    const style = element("select");
    for (const optionText of ["A short explanation", "A numbered list", "A small quiz", "A step-by-step plan"]) {
      const option = element("option", "", optionText);
      style.append(option);
    }
    styleLabel.append(style);
    const preview = element("p", "prompt-preview", "Your example prompt will appear here. Nothing is sent to an AI service.");
    const updatePreview = () => {
      preview.textContent = goal.value.trim()
        ? `Please help with: ${goal.value.trim()}\\nWrite for: A curious 10–12-year-old\\nUse this format: ${style.value}\\nIf you are unsure, say so and suggest how I can check.`
        : "Your example prompt will appear here. Nothing is sent to an AI service.";
    };
    goal.addEventListener("input", updatePreview);
    style.addEventListener("change", updatePreview);
    box.append(goalLabel, styleLabel, preview);
    inner.append(box, element("p", "page-label", "Keep names, addresses, and passwords out of prompts."));
  }

  if (page.links && page.links.length) {
    const links = element("div", "page-links");
    for (const item of page.links) {
      const anchor = safeLink(item);
      if (anchor) links.append(anchor);
    }
    if (links.childElementCount) inner.append(links);
  }
  if (page.items && page.items.length) {
    const list = element("ul", "page-list");
    for (const item of page.items) list.append(element("li", "", item));
    inner.append(list);
  }
  if (page.callout) inner.append(element("div", "page-callout", page.callout));
  if (page.kind === "cover") {
    inner.append(element("div", "cover-rule"));
    inner.append(element("div", "cover-author", "A FRIENDLY GUIDE FOR CURIOUS MINDS"));
  } else {
    inner.append(element("div", "page-label", `THE LIVING AI BOOK  ·  ${String(pageIndex + 1).padStart(2, "0")}`));
  }
  container.append(inner);
}

function updateContents() {
  const list = document.getElementById("contents-list");
  list.replaceChildren();
  for (const item of bookData.contents) {
    const button = element("button", "toc-link");
    button.type = "button";
    button.append(element("span", "toc-number", String(item.number).padStart(2, "0")));
    button.append(element("span", "", item.title));
    button.addEventListener("click", () => { goToPage(item.page); dialog.close(); });
    list.append(button);
  }
}

function renderSpread() {
  const mobile = window.innerWidth <= 720;
  const pagesPerSpread = mobile ? 1 : 2;
  const spread = Math.floor(currentPageIndex / pagesPerSpread);
  const leftIndex = spread * pagesPerSpread;
  const rightIndex = leftIndex + 1;
  renderPage(leftPage, pages[leftIndex], leftIndex, true);
  renderPage(rightPage, pages[rightIndex], rightIndex, !mobile);
  if (mobile) {
    rightPage.classList.remove("active-page");
  }
  const spreadCount = Math.ceil(pages.length / pagesPerSpread);
  document.getElementById("page-number").textContent = mobile
    ? `Page ${leftIndex + 1} of ${pages.length}`
    : `Spread ${spread + 1} of ${spreadCount}`;
  document.getElementById("progress-value").style.width = `${((spread + 1) / spreadCount) * 100}%`;
  document.getElementById("progress-percent").textContent = `${Math.round(((spread + 1) / spreadCount) * 100)}%`;
  previousButton.disabled = currentPageIndex === 0 || turning;
  nextButton.disabled = currentPageIndex + pagesPerSpread >= pages.length || turning;
  updateContents();
}

function goToPage(pageIndex) {
  currentPageIndex = Math.max(0, Math.min(pageIndex, pages.length - 1));
  renderSpread();
}

function turn(direction) {
  const pagesPerSpread = window.innerWidth <= 720 ? 1 : 2;
  const target = currentPageIndex + direction * pagesPerSpread;
  if (turning || target < 0 || target >= pages.length) return;
  turning = true;
  previousButton.disabled = true;
  nextButton.disabled = true;
  bookEl.classList.add(direction > 0 ? "turn-next" : "turn-previous");
  window.setTimeout(() => {
    currentPageIndex = target;
    bookEl.classList.remove("turn-next", "turn-previous");
    turning = false;
    renderSpread();
  }, 220);
}

previousButton.addEventListener("click", () => turn(-1));
nextButton.addEventListener("click", () => turn(1));
document.getElementById("contents-button").addEventListener("click", () => dialog.showModal());
document.getElementById("close-contents").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
window.addEventListener("keydown", event => {
  if (dialog.open) {
    if (event.key === "Escape") dialog.close();
    return;
  }
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const tag = event.target && event.target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (event.target && event.target.isContentEditable)) return;
  if (event.key === "ArrowRight" || event.key === "PageDown") { event.preventDefault(); turn(1); }
  if (event.key === "ArrowLeft" || event.key === "PageUp") { event.preventDefault(); turn(-1); }
  if (event.key === "Home") { event.preventDefault(); goToPage(0); }
  if (event.key === "End") { event.preventDefault(); goToPage(pages.length - 1); }
});
window.addEventListener("resize", renderSpread);

document.getElementById("refresh-button").addEventListener("click", async event => {
  const button = event.currentTarget;
  const status = document.getElementById("news-status");
  const errorBox = document.getElementById("refresh-errors");
  button.disabled = true;
  button.textContent = "Checking…";
  status.textContent = "Checking official news feeds…";
  errorBox.textContent = "";
  try {
    const response = await fetch("/refresh", { method: "POST", headers: { "Accept": "application/json" } });
    if (!response.ok) throw new Error(`The refresh request returned HTTP ${response.status}.`);
    const result = await response.json();
    bookData.pages = result.book.pages;
    bookData.contents = result.book.contents;
    bookData.newsCount = result.book.newsCount;
    pages = bookData.pages;
    if (currentPageIndex >= bookData.pages.length) currentPageIndex = Math.max(0, bookData.pages.length - 1);
    renderSpread();
    status.textContent = `${result.book.newsCount} sourced updates`;
    if (result.errors && result.errors.length) errorBox.textContent = `Some sources could not be checked: ${result.errors.join(" · ")}`;
  } catch (error) {
    errorBox.textContent = `Could not update the news: ${error.message}`;
    status.textContent = "News shelf unchanged";
  } finally {
    button.disabled = false;
    button.innerHTML = '<span aria-hidden="true">↻</span> Update news';
  }
});

document.getElementById("news-status").textContent = `${bookData.newsCount} sourced updates`;
if (bookData.sourceErrors && bookData.sourceErrors.length) {
  document.getElementById("refresh-errors").textContent =
    `Some sources could not be checked: ${bookData.sourceErrors.join(" · ")}`;
}
renderSpread();
</script>
</body>
</html>"""

BOOK_CHAPTERS = (
    {
        "title": "Welcome: your AI explorer's map",
        "sections": (
            (
                "A book that can grow",
                "Artificial intelligence is changing quickly. This book explains the big ideas in simple language, then adds a shelf of recent announcements from official sources. The explanations are the sturdy map; the news shelf is the part that keeps moving.",
            ),
            (
                "How to read it",
                "Pick a chapter from the menu. Try the small activities, follow the source links, and ask questions. You do not need to be a computer expert. Curiosity is enough to get started.",
            ),
            (
                "A helpful rule",
                "AI can be useful, but it can also make mistakes. Treat it like a clever helper that needs checking—not like an all-knowing grown-up.",
            ),
            (
                "AI, or SI?",
                "The established name for this field is artificial intelligence, or AI. “SI” by itself is ambiguous, and “smart intelligence” is not the formal name of the field. You may also hear AGI (artificial general intelligence) or ASI (artificial superintelligence), ideas about much broader or greater-than-human abilities that remain hypothetical. Today's AI tools are not proof that AGI or ASI exists.",
            ),
        ),
        "try": "Open the prompt playground and make a vague request clearer. The book builds the prompt on your device; it does not send it to an AI company.",
    },
    {
        "title": "1. What is artificial intelligence?",
        "sections": (
            (
                "A machine that can do clever-looking tasks",
                "Artificial intelligence, or AI, is a name for computer programs that do tasks we often connect with human thinking. An AI might spot objects in a picture, suggest a route, translate a sentence, or help draft a story.",
            ),
            (
                "Not a tiny person in the computer",
                "An AI program does not have a human body or human life. It can use words that sound friendly, but that does not mean it has feelings, memories, or experiences like you do.",
            ),
            (
                "A simple example",
                "A photo app can learn clues that often appear in pictures of cats, such as ears, eyes, and fur. It uses those clues to make a guess. It can still mistake a toy cat for a real one!",
                "picture-clues",
            ),
        ),
        "try": "Look at three pictures of the same kind of thing. What clues would help a computer tell them apart? What tricky picture might fool it?",
    },
    {
        "title": "2. How can a computer learn?",
        "sections": (
            (
                "Examples are practice",
                "Imagine teaching a computer to sort apples and oranges. You show it many labelled examples. During training, it adjusts its internal settings to get better at matching pictures with labels.",
                "training-examples",
            ),
            (
                "Practice data matters",
                "If most practice pictures show shiny red apples, the computer may struggle with a green apple. If examples leave out important people or situations, its answers may work less well for them.",
            ),
            (
                "It is not learning exactly like you",
                "A computer adjusts numbers in a model. It does not go outside, taste fruit, or understand the experience of eating an apple. The word “learn” is useful, but machine learning is different from a child's learning.",
            ),
        ),
        "try": "Make a pretend training set for sorting shoes and hats. Include unusual examples too—like a hat shaped like a shoe. What could go wrong if all your examples look alike?",
    },
    {
        "title": "3. How does a language model write?",
        "sections": (
            (
                "A very good next-piece guesser",
                "A large language model, or LLM, studies patterns in lots of text. When asked to write, it repeatedly guesses what piece of text should come next. A piece can be a whole word or only part of one.",
                "word-guess",
            ),
            (
                "A tiny pretend example",
                "After “The dog wagged its…”, a person might guess “tail.” A language model compares patterns it learned and picks a likely next piece. It can keep going to make a sentence or a much longer answer.",
            ),
            (
                "A smooth answer can still be wrong",
                "The model is making a pattern-based answer, not checking every sentence against a perfect fact book. It can sound sure and still invent a name, number, or explanation. Check important facts with a trusted person or reliable source.",
                "check-answer",
            ),
        ),
        "try": "Finish “For my science project, I want to learn about…” in three different ways. Notice how a few extra words change what kind of answer would be useful.",
    },
    {
        "title": "4. A timeline of AI",
        "sections": (
            (
                "Big moments, not every moment",
                "AI has a long story with many people, ideas, and inventions. Here are a few milestones—not a complete list. Each one built on earlier work, and none happened all by itself.",
            ),
        ),
        "timeline": AI_TIMELINE,
        "try": "Choose two timeline moments. What changed between them? Which earlier ideas do you think helped make the later moment possible?",
    },
    {
        "title": "5. AI in everyday life",
        "sections": (
            (
                "Helpful jobs for AI",
                "AI can help sort photos, suggest music, translate short messages, read text aloud, find patterns in medical images, or help a person brainstorm. A human should still make important choices and check the result.",
                "seedling",
            ),
            (
                "A schoolwork helper",
                "You could ask for a tricky science idea to be explained in simpler words, then compare the explanation with your textbook. Use help to understand—not to pretend someone else's work is yours.",
            ),
            (
                "A family helper",
                "A family could ask an AI for a list of picnic ideas or a first draft of a packing checklist. A grown-up should check the weather, food safety, and any important details.",
            ),
        ),
        "try": "Use the prompt playground to give an AI helper a clear job, useful details, and a limit. A more careful question often gets a more useful answer.",
    },
    {
        "title": "6. AI applications to explore",
        "sections": (
            (
                "Different tools, different jobs",
                "These are examples of well-known AI products and automation tools—not a ranking or a promise that every feature is available to everyone. Products change, so check each official site for current details. Ask a trusted adult before creating an account, sharing information, or connecting services.",
            ),
        ),
        "applications": AI_APPLICATIONS,
        "try": "Pick one tool and describe its job in one sentence. Is it an AI assistant, an app builder, or a workflow tool? What should a person check before relying on it?",
    },
    {
        "title": "7. Be a smart and safe AI user",
        "sections": (
            (
                "Keep private things private",
                "Do not put passwords, your home address, private photos, school records, or another person's secrets into an AI tool. Ask a parent, guardian, or teacher before trying a new service.",
            ),
            (
                "Check before you share",
                "AI can make up facts or create pictures and voices that look real. For health, money, safety, or school facts, check a reliable source and ask a trusted adult. Do not forward surprising claims just because they look polished.",
            ),
            (
                "Be fair and kind",
                "AI can repeat unfair patterns found in its examples. Think about who might be missing or treated unfairly. Never use AI to bully, trick, or embarrass somebody.",
            ),
            (
                "People are responsible",
                "A person who uses or shares an AI result is still responsible for the choice. AI can suggest; people need to decide whether the suggestion is safe, fair, and true.",
            ),
        ),
        "try": "Before using an AI answer, ask: Who made this? Could it be wrong? Is it private? Who could it affect? Who can help me check?",
    },
    {
        "title": "8. The future: possibilities, not promises",
        "sections": (
            (
                "What might become possible?",
                "People are exploring AI tutors that change their explanations, tools that help doctors study information, robots that assist with repetitive jobs, and creative tools for music, art, and games. These are areas people are working on—not promises that every idea will work.",
            ),
            (
                "Better questions for the future",
                "Will a tool help people learn, or just do their work for them? Who checks mistakes? Does it protect private information? Can people choose not to use it? Who benefits, and who might be left out?",
            ),
            (
                "You can help shape it",
                "The future of AI is not decided by computers alone. Students, families, teachers, scientists, artists, and communities can all help decide which tools are worth building and what rules they should follow.",
            ),
        ),
        "try": "Invent one AI helper for a real problem. Draw or describe it, explain who it helps, and write one safety rule it must follow.",
    },
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self.hidden_depth += 1
        elif tag.lower() in {"p", "br", "div", "li"} and not self.hidden_depth:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag.lower() in {"p", "div", "li"} and not self.hidden_depth:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def clean_html(value: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(value)
    return re.sub(r"\s+", " ", html.unescape(" ".join(extractor.parts))).strip()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, names: set[str]) -> str:
    for child in element:
        if local_name(child.tag) in names:
            if local_name(child.tag) == "link":
                href = child.attrib.get("href")
                if href:
                    return href.strip()
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def parse_published(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def parse_feed(content: bytes, source: str, fetched_at: str) -> list[dict[str, str]]:
    if len(content) > MAX_FEED_BYTES:
        raise ValueError(f"Feed is larger than the {MAX_FEED_BYTES:,}-byte safety limit.")
    root = ET.fromstring(content)
    updates: list[dict[str, str]] = []
    for element in root.iter():
        if local_name(element.tag) not in {"item", "entry"}:
            continue
        title = child_text(element, {"title"})
        link = child_text(element, {"link"})
        summary = child_text(element, {"description", "summary", "content", "encoded"})
        published = child_text(element, {"pubdate", "published", "updated", "date"})
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        identity = link.strip() or f"{source}:{title.strip()}"
        updates.append(
            {
                "id": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                "title": clean_html(title)[:240],
                "summary": clean_html(summary)[:700],
                "url": link.strip(),
                "source": source,
                "published": parse_published(published) or "",
                "fetched_at": fetched_at,
            }
        )
        if len(updates) >= MAX_ITEMS_PER_FEED:
            break
    return updates


def fetch_feed(feed: dict[str, str]) -> tuple[list[dict[str, str]], str | None]:
    request = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "LivingAIBook/1.0 (Python; official public RSS reader)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            content = response.read(MAX_FEED_BYTES + 1)
        fetched_at = datetime.now(timezone.utc).isoformat()
        return parse_feed(content, feed["name"], fetched_at), None
    except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError, ValueError) as error:
        return [], f"{error.__class__.__name__}: {error}"


def empty_update_state() -> dict[str, Any]:
    return {"version": 1, "refreshed_at": "", "updates": [], "source_errors": []}


def load_update_state() -> dict[str, Any]:
    if not UPDATE_FILE.exists():
        return empty_update_state()
    with UPDATE_FILE.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("The local news file has an unsupported format.")
    if not isinstance(value.get("updates"), list) or not isinstance(value.get("source_errors"), list):
        raise ValueError("The local news file is missing its updates or source status.")
    return value


def is_refresh_due(state: dict[str, Any], now: datetime | None = None) -> bool:
    refreshed_at = state.get("refreshed_at", "")
    if not refreshed_at:
        return True
    try:
        previous = datetime.fromisoformat(refreshed_at)
    except (TypeError, ValueError):
        return True
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return current - previous.astimezone(timezone.utc) >= REFRESH_INTERVAL


def combine_updates(
    existing: list[dict[str, Any]], incoming: list[dict[str, str]]
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for update in [*existing, *incoming]:
        identity = update.get("id")
        if isinstance(identity, str) and identity:
            by_id[identity] = update
    combined = list(by_id.values())

    def sort_key(update: dict[str, Any]) -> str:
        return str(update.get("published") or update.get("fetched_at") or "")

    combined.sort(key=sort_key, reverse=True)
    return combined[:MAX_UPDATES]


def save_update_state(state: dict[str, Any]) -> None:
    temporary_file = UPDATE_FILE.with_name(f"{UPDATE_FILE.name}.tmp")
    try:
        with temporary_file.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_file, UPDATE_FILE)
    except OSError:
        if temporary_file.exists():
            temporary_file.unlink()
        raise


def refresh_updates(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    state = existing if existing is not None else load_update_state()
    now = datetime.now(timezone.utc).isoformat()
    incoming: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(FEEDS)) as executor:
        futures = {executor.submit(fetch_feed, feed): feed for feed in FEEDS}
        for future, feed in futures.items():
            updates, error = future.result()
            incoming.extend(updates)
            if error:
                errors.append({"source": feed["name"], "error": error})
    state = {
        "version": 1,
        "refreshed_at": now,
        "updates": combine_updates(state.get("updates", []), incoming),
        "source_errors": errors,
    }
    save_update_state(state)
    return state


def chapter_from_update(update: dict[str, Any]) -> dict[str, Any]:
    published = update.get("published")
    if published:
        try:
            date_label = datetime.fromisoformat(published).strftime("%B %d, %Y")
        except ValueError:
            date_label = "Date not provided by the source"
    else:
        date_label = "Date not provided by the source"
    return {
        "title": f"News: {update['title']}",
        "source": update["source"],
        "source_url": update["url"],
        "date_label": date_label,
        "summary": update.get("summary") or "The source did not provide a short description.",
    }


def print_terminal_book(state: dict[str, Any]) -> None:
    print(f"\n{APP_TITLE}")
    print("=" * len(APP_TITLE))
    print("A kid-friendly guide to artificial intelligence for curious readers ages 10–12.\n")
    for chapter in BOOK_CHAPTERS:
        print(f"\n{chapter['title']}")
        print("-" * len(chapter["title"]))
        for section in chapter["sections"]:
            print(f"\n{section[0]}\n{section[1]}")
        for event in chapter.get("timeline", ()):
            print(f"\n{event['year']}: {event['title']}\n{event['text']}")
            print(f"Source: {event['source']} — {event['url']}")
        for application in chapter.get("applications", ()):
            print(
                f"\n{application['name']} — {application['category']}\n"
                f"{application['description']}\n"
                f"When to use it: {application['use_when']}\n"
                f"Official site: {application['url']}"
            )
        print(f"\nTry it: {chapter['try']}")
    updates = state.get("updates", [])
    print("\nLatest AI developments")
    print("----------------------")
    if not updates:
        print("No announcements are saved yet. Run: python living_ai_book.py --refresh")
    for item in updates[:10]:
        chapter = chapter_from_update(item)
        print(f"\n{chapter['title']} ({chapter['date_label']}; {chapter['source']})")
        print(chapter["summary"])
        print(chapter["source_url"])
    print("\nRemember: news headlines are not proof that a tool works perfectly.")
    print(f"\n{AUTHOR_PAGE['title']}")
    print("-" * len(AUTHOR_PAGE["title"]))
    print(f"\n{AUTHOR_PAGE['name']}\n{AUTHOR_PAGE['bio']}")
    print(f"\nLinkedIn: {AUTHOR_PAGE['profile_url']}")


def build_book_data(state: dict[str, Any]) -> dict[str, Any]:
    pages: list[dict[str, Any]] = [
        {
            "kind": "cover",
            "kicker": "A curious reader's guide",
            "title": "The Living AI Book",
            "illustration": "reader-robot",
            "paragraphs": [
                "How clever computers learn, what they can do, and how we can shape what comes next."
            ],
        },
        {
            "kind": "contents",
            "kicker": "A map for your journey",
            "title": "Inside this book",
            "paragraphs": [
                "Choose a chapter below, or use the arrow keys to turn one spread at a time."
            ],
        },
    ]
    contents: list[dict[str, Any]] = []
    updates = state.get("updates", [])
    updates_by_topic: dict[str, list[dict[str, Any]]] = {}
    for item in updates:
        updates_by_topic.setdefault(related_chapter(item), []).append(item)

    def add_toc_entry(title: str, page_index: int) -> None:
        contents.append(
            {"number": len(contents) + 1, "title": title, "page": page_index}
        )

    for chapter in BOOK_CHAPTERS:
        add_toc_entry(chapter["title"], len(pages))
        for index, section in enumerate(chapter["sections"]):
            page = {
                "kind": "chapter",
                "kicker": chapter["title"] if index == 0 else "Keep exploring",
                "title": section[0],
                "paragraphs": [section[1]],
            }
            if len(section) > 2:
                page["illustration"] = section[2]
            pages.append(page)
        for index, event in enumerate(chapter.get("timeline", ())):
            pages.append(
                {
                    "kind": "timeline-event",
                    "kicker": event["year"],
                    "title": event["title"],
                    "paragraphs": [event["text"]],
                    "illustration": "timeline" if index == 0 else "",
                    "links": [{"label": event["source"], "url": event["url"]}],
                }
            )
        if chapter.get("applications"):
            pages.append(
                {
                    "kind": "applications",
                    "kicker": "A quick guide",
                    "title": "Which tool for which task?",
                    "paragraphs": [
                        "These tools have different jobs. Pick one that fits your task, and check its answer or result."
                    ],
                    "applications": list(chapter["applications"]),
                    "callout": (
                        "The website and its features may change. Ask a trusted adult before "
                        "signing up or sharing personal information."
                    ),
                }
            )
        pages.append(
            {
                "kind": "activity",
                "kicker": "Your turn",
                "title": "Try it yourself",
                "paragraphs": ["Pause and explore this idea in your own way."],
                "callout": chapter["try"],
            }
        )
        if chapter["title"].startswith("5."):
            pages.append(
                {
                    "kind": "prompt-builder",
                    "kicker": "An interactive activity",
                    "title": "The prompt playground",
                    "paragraphs": [
                        "A prompt is an instruction for an AI tool. Build a clearer example and see how small details can guide an answer."
                    ],
                }
            )
        topic_updates = updates_by_topic.get(chapter["title"], [])
        if topic_updates:
            field_title = f"New field notes: {chapter['title']}"
            add_toc_entry(field_title, len(pages))
            pages.append(
                {
                    "kind": "field-notes",
                    "kicker": "A living chapter",
                    "title": "New field notes",
                    "paragraphs": [
                        f"{len(topic_updates)} recent announcement(s) connect to “{chapter['title']}”. These source-linked notes add current examples alongside the book's stable explanation."
                    ],
                    "links": [
                        {
                            "label": f"{item.get('source', 'Source')}: {item.get('title', 'AI announcement')}",
                            "url": item.get("url", ""),
                        }
                        for item in topic_updates
                    ],
                    "callout": (
                        "These are announcements from their publishers, not independent tests. "
                        "Read the linked source and ask what evidence would help check the claims."
                    ),
                }
            )

    if updates:
        add_toc_entry("Recent AI announcements", len(pages))
        pages.append(
            {
                "kind": "section",
                "kicker": "A changing field",
                "title": "Recent AI announcements",
                "paragraphs": [
                    f"This living edition includes {len(updates)} announcements from official company and research feeds. Choose an update in the contents to read its source and summary."
                ],
                "callout": (
                    "An announcement is a claim from its publisher, not an independent test. "
                    "Read the source and ask what evidence would help check it."
                ),
            }
        )
        for item in updates:
            chapter = chapter_from_update(item)
            related = related_chapter(item)
            add_toc_entry(chapter["title"], len(pages))
            pages.append(
                {
                    "kind": "news",
                    "kicker": f"{chapter['source']} · {chapter['date_label']} · Related: {related}",
                    "title": item["title"],
                    "paragraphs": [
                        chapter["summary"],
                        f"This update is connected to: {related}. What does the announcement actually say? Which details would you want to test? Ask a trusted adult to help check important claims.",
                    ],
                    "links": [
                        {
                            "label": "Read the original announcement",
                            "url": chapter["source_url"],
                        }
                    ],
                    "callout": (
                        "This summary comes from the linked source. It is not an independent "
                        "fact-check or a promise about what AI can do."
                    ),
                }
            )

    news_pages = [
        {
            "label": f"{feed['name']} announcements",
            "url": feed["news_page"],
        }
        for feed in FEEDS
    ]
    news_pages.extend(
        [
            {
                "label": "Anthropic announcements",
                "url": "https://www.anthropic.com/news",
            },
            {
                "label": "Microsoft AI news",
                "url": "https://news.microsoft.com/source/topics/ai/",
            },
        ]
    )
    add_toc_entry("Official news pages", len(pages))
    pages.append(
        {
            "kind": "sources",
            "kicker": "Go to the source",
            "title": "Official AI news pages",
            "paragraphs": [
                "Visit these publishers' pages to read announcements in their original context."
            ],
            "links": news_pages,
        }
    )

    add_toc_entry(AUTHOR_PAGE["title"], len(pages))
    pages.append(
        {
            "kind": "author",
            "kicker": "About the author",
            "title": AUTHOR_PAGE["name"],
            "paragraphs": [AUTHOR_PAGE["bio"]],
            "links": [
                {
                    "label": "Visit Harit on LinkedIn",
                    "url": AUTHOR_PAGE["profile_url"],
                }
            ],
            "callout": "Thank you for reading. Stay curious, kind, and thoughtful about the tools we build.",
        }
    )
    return {
        "pages": pages,
        "contents": contents,
        "newsCount": len(updates),
        "sourceErrors": [
            f"{item.get('source', 'Source')}: {item.get('error', 'Unknown error')}"
            for item in state.get("source_errors", [])
        ],
        "refreshedAt": state.get("refreshed_at", ""),
    }


def related_chapter(update: dict[str, Any]) -> str:
    text = f"{update.get('title', '')} {update.get('summary', '')}".casefold()
    topics = (
        (
            "7. Be a smart and safe AI user",
            ("safety", "safe", "privacy", "security", "responsible", "misuse", "trust"),
        ),
        (
            "6. AI applications to explore",
            ("chatgpt", "gemini", "claude", "lovable", "n8n", "workflow automation", "app builder"),
        ),
        (
            "4. A timeline of AI",
            ("turing", "dartmouth", "deep blue", "eliza", "imagenet", "alexnet", "timeline", "nobel"),
        ),
        (
            "3. How does a language model write?",
            ("language model", "llm", "chatbot", "generative", "reasoning", "assistant"),
        ),
        (
            "2. How can a computer learn?",
            ("model", "training", "learn", "research", "benchmark", "dataset"),
        ),
        (
            "5. AI in everyday life",
            ("education", "school", "health", "robot", "workplace", "productivity"),
        ),
        (
            "8. The future: possibilities, not promises",
            ("future", "agi", "superintelligence", "artificial general intelligence"),
        ),
    )
    for chapter, keywords in topics:
        if any(keyword in text for keyword in keywords):
            return chapter
    return "8. The future: possibilities, not promises"


def export_pwa_data(state: dict[str, Any] | None = None) -> Path:
    current = state if state is not None else load_update_state()
    PWA_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_book_data(current)
    temporary_file = PWA_DATA_FILE.with_name(f"{PWA_DATA_FILE.name}.tmp")
    try:
        with temporary_file.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_file, PWA_DATA_FILE)
    except OSError:
        if temporary_file.exists():
            temporary_file.unlink()
        raise
    return PWA_DATA_FILE


def render_browser_document(state: dict[str, Any]) -> str:
    data = json.dumps(build_book_data(state), ensure_ascii=True, separators=(",", ":"))
    data = (
        data.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return BROWSER_TEMPLATE.replace("__BOOK_DATA__", data)


def refresh_startup_state() -> dict[str, Any]:
    state = load_update_state()
    if is_refresh_due(state):
        try:
            return refresh_updates(state)
        except OSError as error:
            print(f"Could not save the latest news; showing saved updates: {error}", file=sys.stderr)
    return state


def launch_book_server(port: int = 8765, open_browser: bool = True) -> int:
    try:
        state = refresh_startup_state()
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"Could not load the book's local news file: {error}", file=sys.stderr)
        return 1

    class BookRequestHandler(BaseHTTPRequestHandler):
        asset_types = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
            "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
            "/icon.svg": ("icon.svg", "image/svg+xml"),
            "/icon-192.png": ("icon-192.png", "image/png"),
            "/icon-512.png": ("icon-512.png", "image/png"),
        }

        def send_body(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "manifest-src 'self'; worker-src 'self'; connect-src 'self'; base-uri 'self'; "
                "form-action 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            request_path = unquote(urlsplit(self.path).path)
            if request_path == "/book-data.json":
                payload = build_book_data(self.server.book_state)
                payload["localRefreshEndpoint"] = True
                body = json.dumps(
                    payload, ensure_ascii=True
                ).encode("utf-8")
                self.send_body(
                    HTTPStatus.OK,
                    body,
                    "application/json; charset=utf-8",
                )
                return
            asset = self.asset_types.get(request_path)
            if asset is None:
                self.send_body(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
                return
            file_name, content_type = asset
            try:
                body = (PWA_DIR / file_name).read_bytes()
            except OSError as error:
                self.send_body(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    str(error).encode("utf-8"),
                    "text/plain; charset=utf-8",
                )
                return
            self.send_body(HTTPStatus.OK, body, content_type)

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/api/refresh":
                self.send_body(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
                return
            origin = self.headers.get("Origin")
            accepted_origins = {
                f"http://127.0.0.1:{self.server.server_port}",
                f"http://localhost:{self.server.server_port}",
            }
            if origin and origin not in accepted_origins:
                self.send_body(HTTPStatus.FORBIDDEN, b"Invalid request origin", "text/plain; charset=utf-8")
                return
            try:
                new_state = refresh_updates(self.server.book_state)
            except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
                message = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_body(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    message,
                    "application/json; charset=utf-8",
                )
                return
            self.server.book_state = new_state
            try:
                export_pwa_data(new_state)
            except OSError as error:
                message = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_body(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    message,
                    "application/json; charset=utf-8",
                )
                return
            body = json.dumps(build_book_data(new_state), ensure_ascii=True).encode("utf-8")
            self.send_body(HTTPStatus.OK, body, "application/json; charset=utf-8")

        def log_message(self, format_string: str, *args: Any) -> None:
            return

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), BookRequestHandler)
    except OSError as error:
        print(f"Could not start the local book server on port {port}: {error}", file=sys.stderr)
        return 1
    server.daemon_threads = True
    server.book_state = state
    address = f"http://127.0.0.1:{server.server_port}/"
    print(f"{APP_TITLE} is ready at {address}")
    print("This book is served only on your computer. Press Ctrl+C to close it.")
    if open_browser:
        timer = threading.Timer(0.5, webbrowser.open, args=(address,))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nClosing the book.")
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Read the chapters in this terminal without opening a browser.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch official announcement feeds now and save the updates.",
    )
    parser.add_argument(
        "--export-pwa-data",
        action="store_true",
        help="Write the current book edition to pwa/book-data.json.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Local browser-server port (use 0 to choose an available port).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the local book server without opening a browser tab.",
    )
    arguments = parser.parse_args()

    if not 0 <= arguments.port <= 65535:
        parser.error("--port must be between 0 and 65535.")

    if arguments.terminal:
        try:
            print_terminal_book(load_update_state())
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
            print(f"Could not read the local news file: {error}", file=sys.stderr)
            return 1
        return 0

    if arguments.refresh:
        try:
            state = refresh_updates()
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
            print(f"Could not refresh or save the news: {error}", file=sys.stderr)
            return 1
        print(f"Saved {len(state['updates'])} sourced updates to {UPDATE_FILE}.")
        for item in state["source_errors"]:
            print(f"Could not check {item['source']}: {item['error']}", file=sys.stderr)
        if arguments.export_pwa_data:
            try:
                print(f"Exported PWA book data to {export_pwa_data(state)}.")
            except OSError as error:
                print(f"Could not export PWA book data: {error}", file=sys.stderr)
                return 1
        if len(state["source_errors"]) == len(FEEDS):
            return 1
        return 0

    if arguments.export_pwa_data:
        try:
            print(f"Exported PWA book data to {export_pwa_data()}.")
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
            print(f"Could not export PWA book data: {error}", file=sys.stderr)
            return 1
        return 0

    return launch_book_server(port=arguments.port, open_browser=not arguments.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
