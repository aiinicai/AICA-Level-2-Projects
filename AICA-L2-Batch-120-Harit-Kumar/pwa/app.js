"use strict";

const leftPage = document.getElementById("left-page");
const rightPage = document.getElementById("right-page");
const bookElement = document.getElementById("book");
const previousButton = document.getElementById("previous-button");
const nextButton = document.getElementById("next-button");
const contentsDialog = document.getElementById("contents-dialog");
const refreshButton = document.getElementById("refresh-button");
const installButton = document.getElementById("install-button");
let bookData = null;
let currentPageIndex = 0;
let turning = false;
let pendingInstall = null;
let touchStartX = null;

const NEWS_REFRESH_INTERVAL = 60 * 60 * 1000;
const LOCAL_EDITION_KEY = "living-ai-book-offline-edition-v1";

function makeElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function isTrustedWebLink(value) {
  try {
    const link = new URL(value);
    return link.protocol === "https:" || link.protocol === "http:";
  } catch {
    return false;
  }
}

function showNotice(message, warning = false) {
  const node = document.getElementById("refresh-errors");
  node.textContent = message;
  node.hidden = !message;
  node.classList.toggle("notice-warning", warning);
}

function makeExternalLink(link) {
  if (!link || !isTrustedWebLink(link.url)) return null;
  const anchor = makeElement("a", "page-link", link.label || link.url);
  anchor.href = link.url;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  return anchor;
}

const BOOK_ILLUSTRATIONS = Object.freeze({
  "reader-robot": { svg: `<svg viewBox="0 0 180 132" aria-hidden="true"><path d="M30 111h120" stroke="#d8c58f" stroke-width="3" stroke-linecap="round"/><path d="M69 36V25m42 11V25" stroke="#f0d38a" stroke-width="4" stroke-linecap="round"/><circle cx="69" cy="22" r="5" fill="#f0d38a"/><circle cx="111" cy="22" r="5" fill="#f0d38a"/><rect x="50" y="34" width="80" height="63" rx="20" fill="#f3dca4" stroke="#263f34" stroke-width="4"/><path d="M66 60h12m24 0h12" stroke="#315643" stroke-width="7" stroke-linecap="round"/><path d="M76 77q14 13 28 0" fill="none" stroke="#b56e51" stroke-width="4" stroke-linecap="round"/><path d="M61 99 43 111m76-12 18 12" stroke="#f3dca4" stroke-width="8" stroke-linecap="round"/><path d="M42 72 31 79m107-7 11 7" stroke="#f3dca4" stroke-width="7" stroke-linecap="round"/><path d="M49 101q-16-10-26-2v17h30m78-15q16-10 26-2v17h-30" fill="#fbf3dd" stroke="#c5a768" stroke-width="3" stroke-linejoin="round"/><path d="M90 103v13m-27-13q13 10 27 10m27-10q-13 10-27 10" fill="none" stroke="#bd985d" stroke-width="2"/></svg>`, caption: "A friendly guide for curious minds." },
  "seedling": { svg: `<svg viewBox="0 0 120 100" aria-hidden="true"><path d="M60 79V39" stroke="#315643" stroke-width="5" stroke-linecap="round"/><path d="M59 54C37 55 28 43 31 28c18 0 30 7 28 26Zm3-10c2-19 15-29 32-25-2 17-12 27-32 25Z" fill="#9cbe83" stroke="#315643" stroke-width="3" stroke-linejoin="round"/><path d="M39 78h42l-6 16H45Z" fill="#d89c70" stroke="#8c573d" stroke-width="3" stroke-linejoin="round"/><path d="M36 77h48" stroke="#8c573d" stroke-width="4" stroke-linecap="round"/><circle cx="91" cy="21" r="8" fill="#f0d38a"/><path d="m90 8 1-4m12 17 4 1M81 16l-4-3" stroke="#bd985d" stroke-width="2" stroke-linecap="round"/></svg>`, caption: "Small helpful tools can grow into big ideas." },
  "timeline": { svg: `<svg viewBox="0 0 150 100" aria-hidden="true"><path d="M20 72h110" stroke="#c8b17a" stroke-width="4" stroke-linecap="round"/><circle cx="31" cy="72" r="7" fill="#d9946e"/><circle cx="75" cy="72" r="7" fill="#88a776"/><circle cx="119" cy="72" r="7" fill="#7893a5"/><path d="M75 62V34" stroke="#315643" stroke-width="3"/><circle cx="75" cy="26" r="19" fill="#f4e4b9" stroke="#315643" stroke-width="3"/><path d="M75 14v12l9 5" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="m29 57 3-10 3 10m40-2 3-10 3 10m40 2 3-10 3 10" fill="#fffdf7" stroke="#bd985d" stroke-width="2" stroke-linejoin="round"/><path d="M27 88h8m36 0h8m36 0h8" stroke="#c8b17a" stroke-width="2" stroke-linecap="round"/></svg>`, caption: "AI has many milestones, not just one big invention." },
  "training-examples": { svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="10" y="16" width="94" height="88" rx="14" fill="#f8f0dc" stroke="#cdb782" stroke-width="2"/><circle cx="39" cy="50" r="16" fill="#df8063"/><path d="M39 32q-2-9 7-9m-7 9q-9-8-14-1" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><circle cx="76" cy="50" r="16" fill="#efbd65"/><path d="M76 31q4-8 10-5" fill="none" stroke="#75945f" stroke-width="3" stroke-linecap="round"/><text x="57" y="88" text-anchor="middle" font-size="12" fill="#45564a">labelled pictures</text><path d="M111 60h29m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="149" y="22" width="66" height="76" rx="19" fill="#dce8dc" stroke="#315643" stroke-width="3"/><circle cx="172" cy="51" r="4" fill="#315643"/><circle cx="192" cy="51" r="4" fill="#315643"/><path d="M171 68q10 8 21 0" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><text x="182" y="91" text-anchor="middle" font-size="11" fill="#315643">practice</text><path d="M222 60h29m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="260" y="23" width="70" height="76" rx="13" fill="#fff9ec" stroke="#cdb782" stroke-width="2"/><circle cx="280" cy="51" r="12" fill="#df8063"/><circle cx="310" cy="51" r="12" fill="#efbd65"/><text x="295" y="88" text-anchor="middle" font-size="12" fill="#45564a">new guesses</text></svg>`, caption: "Examples go in; the computer practises spotting patterns." },
  "word-guess": { svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="8" y="35" width="105" height="52" rx="12" fill="#f8f0dc" stroke="#cdb782" stroke-width="2"/><text x="60" y="57" text-anchor="middle" font-size="12" fill="#45564a">“The dog wagged</text><text x="60" y="75" text-anchor="middle" font-size="12" fill="#45564a">its…”</text><path d="M120 61h24m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="150" y="29" width="68" height="64" rx="19" fill="#dce8dc" stroke="#315643" stroke-width="3"/><circle cx="173" cy="53" r="4" fill="#315643"/><circle cx="195" cy="53" r="4" fill="#315643"/><path d="M171 69q12 7 24 0" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><path d="M224 61h24m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="255" y="35" width="77" height="52" rx="12" fill="#e9f0e5" stroke="#91ad7b" stroke-width="2"/><text x="293" y="67" text-anchor="middle" font-size="16" font-weight="700" fill="#315643">“tail”</text><text x="184" y="112" text-anchor="middle" font-size="11" fill="#667064">guesses a likely next piece</text></svg>`, caption: "It predicts a likely next word; it is not looking up a perfect answer." },
  "check-answer": { svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="10" y="29" width="102" height="68" rx="14" fill="#dce8dc" stroke="#315643" stroke-width="2"/><circle cx="42" cy="53" r="4" fill="#315643"/><circle cx="78" cy="53" r="4" fill="#315643"/><path d="M42 68q18 10 36 0" fill="none" stroke="#315643" stroke-width="3" stroke-linecap="round"/><path d="M62 22v-8m-17 11-5-7m39 7 5-7" stroke="#bd985d" stroke-width="3" stroke-linecap="round"/><text x="61" y="88" text-anchor="middle" font-size="11" fill="#45564a">AI suggests</text><path d="M120 62h25m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="188" cy="49" r="18" fill="#e7b18c" stroke="#845b49" stroke-width="2"/><path d="M158 103q3-31 30-31t30 31" fill="#7893a5" stroke="#496676" stroke-width="2"/><path d="M211 56h25m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="246" y="26" width="82" height="77" rx="5" fill="#fff9ec" stroke="#cdb782" stroke-width="2"/><path d="M260 44h50m-50 13h43m-43 13h50m-50 13h36" stroke="#b8aa8e" stroke-width="3" stroke-linecap="round"/><text x="287" y="117" text-anchor="middle" font-size="11" fill="#45564a">person checks a book</text></svg>`, caption: "A person checks important answers with a trusted source." },
  "picture-clues": { svg: `<svg viewBox="0 0 340 126" aria-hidden="true"><rect x="12" y="24" width="94" height="78" rx="12" fill="#f6f0df" stroke="#cdb782" stroke-width="2"/><path d="m31 54 8-18 17 12m18 6 16-18 8 18" fill="#e7b18c" stroke="#845b49" stroke-width="3" stroke-linejoin="round"/><circle cx="57" cy="70" r="24" fill="#e7b18c" stroke="#845b49" stroke-width="3"/><circle cx="49" cy="69" r="3" fill="#263f34"/><circle cx="65" cy="69" r="3" fill="#263f34"/><path d="M53 80q4 4 8 0" fill="none" stroke="#845b49" stroke-width="2"/><path d="M119 62h30m-8-8 8 8-8 8" fill="none" stroke="#bd985d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="187" cy="52" r="23" fill="#dce8dc" stroke="#315643" stroke-width="3"/><path d="M204 69 220 86" stroke="#315643" stroke-width="6" stroke-linecap="round"/><circle cx="181" cy="48" r="4" fill="#315643"/><circle cx="194" cy="48" r="4" fill="#315643"/><path d="M179 60q8 6 16 0" fill="none" stroke="#315643" stroke-width="2"/><text x="274" y="48" text-anchor="middle" font-size="12" fill="#45564a">pointy ears?</text><text x="274" y="69" text-anchor="middle" font-size="12" fill="#45564a">whiskers?</text><text x="274" y="95" text-anchor="middle" font-size="12" font-weight="700" fill="#315643">maybe a cat!</text></svg>`, caption: "The app looks for clues—ears and whiskers—but can still be fooled." }
});

function renderIllustration(container, illustration) {
  const drawing = BOOK_ILLUSTRATIONS[illustration];
  if (!drawing) return;
  const wrapper = makeElement("figure", `book-cartoon cartoon-${illustration}`);
  wrapper.innerHTML = drawing.svg;
  wrapper.append(makeElement("figcaption", "cartoon-caption", drawing.caption));
  container.append(wrapper);
}

function renderPromptBuilder(container) {
  const box = makeElement("div", "prompt-builder");
  const goalLabel = makeElement("label", "", "What would you like help with?");
  const goal = makeElement("input");
  goal.maxLength = 180;
  goal.placeholder = "For example: explain how rainbows form";
  goalLabel.append(goal);

  const styleLabel = makeElement("label", "", "What kind of answer would help?");
  const style = makeElement("select");
  for (const label of ["A short explanation", "A numbered list", "A small quiz", "A step-by-step plan"]) {
    style.append(makeElement("option", "", label));
  }
  styleLabel.append(style);

  const preview = makeElement(
    "p",
    "prompt-preview",
    "Your example prompt will appear here. Nothing is sent to an AI service."
  );
  const updatePreview = () => {
    preview.textContent = goal.value.trim()
      ? `Please help with: ${goal.value.trim()}\nWrite for: A curious 10–12-year-old\nUse this format: ${style.value}\nIf you are unsure, say so and suggest how I can check.`
      : "Your example prompt will appear here. Nothing is sent to an AI service.";
  };
  goal.addEventListener("input", updatePreview);
  style.addEventListener("change", updatePreview);
  box.append(goalLabel, styleLabel, preview);
  container.append(box);
}

function renderPage(container, page, pageIndex, active) {
  container.replaceChildren();
  container.classList.toggle("active-page", active);
  container.setAttribute("aria-hidden", String(!active));
  container.classList.remove("cover-page", "empty-page");
  if (!page) {
    container.classList.add("empty-page");
    container.append(makeElement("span", "", "The Living AI Book"));
    return;
  }
  if (page.kind === "cover") container.classList.add("cover-page");
  if (page.kind === "timeline-event") container.classList.add("timeline-page");
  container.classList.toggle("application-page", page.kind === "applications");

  const content = makeElement("div", "page-content");
  if (page.kicker) content.append(makeElement("div", "page-kicker", page.kicker));
  if (page.title) content.append(makeElement("h2", "", page.title));
  for (const paragraph of page.paragraphs || []) content.append(makeElement("p", "", paragraph));
  if (page.illustration) renderIllustration(content, page.illustration);

  if (page.kind === "contents") {
    content.append(renderContentsList(bookData.contents, true));
  }
  if (page.kind === "applications" && page.applications?.length) {
    const list = makeElement("div", "application-list");
    for (const application of page.applications) {
      const entry = makeElement("section", "application-entry");
      const heading = makeElement("h3");
      const anchor = makeExternalLink({ label: application.name, url: application.url });
      if (anchor) heading.append(anchor);
      entry.append(heading);
      entry.append(makeElement("p", "application-description", application.description));
      entry.append(makeElement("p", "application-use", `Use it when: ${application.use_when}`));
      list.append(entry);
    }
    content.append(list);
  }
  if (page.kind === "prompt-builder") renderPromptBuilder(content);
  if (page.links?.length) {
    const links = makeElement("div", "page-links");
    for (const link of page.links) {
      const anchor = makeExternalLink(link);
      if (anchor) links.append(anchor);
    }
    if (links.childElementCount) content.append(links);
  }
  if (page.items?.length) {
    const list = makeElement("ul", "page-list");
    for (const item of page.items) list.append(makeElement("li", "", item));
    content.append(list);
  }
  if (page.kind === "cover") content.append(makeElement("div", "cover-rule"));
  if (page.callout) content.append(makeElement("div", "page-callout", page.callout));
  content.append(makeElement(
    "p",
    "page-label",
    page.kind === "cover" ? "A FRIENDLY GUIDE FOR CURIOUS MINDS" : `THE LIVING AI BOOK · ${String(pageIndex + 1).padStart(2, "0")}`
  ));
  container.append(content);
}

function renderContentsList(items, compact = false) {
  const list = makeElement("div", compact ? "table-of-contents compact-toc" : "table-of-contents");
  for (const item of items || []) {
    const button = makeElement("button", "toc-link");
    button.type = "button";
    button.append(makeElement("span", "toc-number", String(item.number).padStart(2, "0")));
    button.append(makeElement("span", "toc-title", item.title));
    button.addEventListener("click", () => {
      goToPage(item.page);
      if (contentsDialog.open) contentsDialog.close();
    });
    list.append(button);
  }
  return list;
}

function renderDialogContents() {
  document.getElementById("contents-list").replaceChildren(renderContentsList(bookData?.contents));
}

function updateNavigation() {
  const mobile = window.matchMedia("(max-width: 760px)").matches;
  const pagesPerView = mobile ? 1 : 2;
  const viewNumber = Math.floor(currentPageIndex / pagesPerView);
  const viewCount = Math.ceil(bookData.pages.length / pagesPerView);
  document.getElementById("page-number").textContent = mobile
    ? `Page ${currentPageIndex + 1} of ${bookData.pages.length}`
    : `Spread ${viewNumber + 1} of ${viewCount}`;
  document.getElementById("progress-value").style.width = `${((viewNumber + 1) / viewCount) * 100}%`;
  document.getElementById("progress-percent").textContent = `${Math.round(((viewNumber + 1) / viewCount) * 100)}%`;
  previousButton.disabled = currentPageIndex <= 0 || turning;
  nextButton.disabled = currentPageIndex + pagesPerView >= bookData.pages.length || turning;
}

function renderBook() {
  if (!bookData?.pages?.length) return;
  const mobile = window.matchMedia("(max-width: 760px)").matches;
  const pagesPerView = mobile ? 1 : 2;
  currentPageIndex = Math.min(currentPageIndex, bookData.pages.length - 1);
  if (mobile) {
    renderPage(leftPage, bookData.pages[currentPageIndex], currentPageIndex, true);
    renderPage(rightPage, null, currentPageIndex + 1, false);
  } else {
    const spreadStart = Math.floor(currentPageIndex / 2) * 2;
    renderPage(leftPage, bookData.pages[spreadStart], spreadStart, true);
    renderPage(rightPage, bookData.pages[spreadStart + 1], spreadStart + 1, true);
  }
  updateNavigation();
}

function goToPage(pageIndex) {
  if (!bookData?.pages?.length) return;
  const clamped = Math.max(0, Math.min(Math.floor(pageIndex), bookData.pages.length - 1));
  currentPageIndex = window.matchMedia("(max-width: 760px)").matches
    ? clamped
    : Math.floor(clamped / 2) * 2;
  renderBook();
}

function turnPage(direction) {
  if (!bookData || turning) return;
  const step = window.matchMedia("(max-width: 760px)").matches ? 1 : 2;
  const nextIndex = currentPageIndex + direction * step;
  if (nextIndex < 0 || nextIndex >= bookData.pages.length) return;
  turning = true;
  updateNavigation();
  bookElement.classList.add(direction > 0 ? "turn-next" : "turn-previous");
  window.setTimeout(() => {
    currentPageIndex = nextIndex;
    turning = false;
    bookElement.classList.remove("turn-next", "turn-previous");
    renderBook();
  }, 230);
}

function displayEditionStatus() {
  const status = document.getElementById("news-status");
  const editionDate = document.getElementById("edition-date");
  const count = bookData.newsCount || 0;
  status.textContent = `${count} sourced update${count === 1 ? "" : "s"} in this edition`;
  if (bookData.refreshedAt) {
    const date = new Date(bookData.refreshedAt);
    if (!Number.isNaN(date.valueOf())) editionDate.textContent = `Edition data checked ${date.toLocaleString()}.`;
  }
  if (bookData.sourceErrors?.length) {
    showNotice(`Some sources could not be checked: ${bookData.sourceErrors.join(" · ")}`, true);
  }
}

function saveEditionLocally(data) {
  try {
    localStorage.setItem(LOCAL_EDITION_KEY, JSON.stringify(data));
  } catch {
    // The service worker cache remains the offline fallback if browser storage is unavailable.
  }
}

async function fetchPublishedEdition() {
  const url = new URL("./book-data.json", document.baseURI);
  url.searchParams.set("check", String(Date.now()));
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`The book server returned HTTP ${response.status}.`);
  const data = await response.json();
  if (!Array.isArray(data.pages) || !Array.isArray(data.contents)) {
    throw new Error("The published book data has an unexpected format.");
  }
  return data;
}

async function fetchLocalEditionUpdate() {
  const response = await fetch(new URL("./api/refresh", document.baseURI), {
    method: "POST",
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  if ([404, 405, 501].includes(response.status)) return null;
  if (!response.ok) throw new Error(`The local book server returned HTTP ${response.status}.`);
  const data = await response.json();
  if (!Array.isArray(data.pages) || !Array.isArray(data.contents)) {
    throw new Error("The refreshed book data has an unexpected format.");
  }
  return data;
}

function loadSavedEdition() {
  try {
    const serialized = localStorage.getItem(LOCAL_EDITION_KEY);
    if (!serialized) return null;
    const data = JSON.parse(serialized);
    return Array.isArray(data.pages) && Array.isArray(data.contents) ? data : null;
  } catch {
    return null;
  }
}

async function checkForUpdates({ manual = false } = {}) {
  if (!navigator.onLine) {
    document.getElementById("offline-note").hidden = false;
    if (manual) showNotice("You're offline. The saved edition is available, and updates will be checked when you reconnect.");
    return;
  }
  refreshButton.disabled = true;
  refreshButton.setAttribute("aria-busy", "true");
  if (manual) refreshButton.lastChild.textContent = " Checking…";
  try {
    const latest = manual && bookData?.localRefreshEndpoint
      ? await fetchLocalEditionUpdate()
      : null;
    const edition = latest || await fetchPublishedEdition();
    const oldEdition = bookData?.refreshedAt || "";
    bookData = edition;
    saveEditionLocally(edition);
    document.getElementById("offline-note").hidden = true;
    showNotice("");
    displayEditionStatus();
    renderBook();
    renderDialogContents();
    if (manual && oldEdition && oldEdition !== (edition.refreshedAt || "")) {
      showNotice("A newer edition is ready. Its chapters and field notes are now on the shelf.");
    } else if (manual) {
      showNotice("You have the latest published edition.");
    }
  } catch (error) {
    if (!bookData) {
      bookData = loadSavedEdition();
      if (bookData) {
        renderBook();
        renderDialogContents();
        displayEditionStatus();
      }
    }
    if (!bookData) {
      showNotice(`Could not load the book edition: ${error.message}`, true);
    } else if (manual) {
      showNotice(`Could not check for a newer edition. Your saved book is still available. ${error.message}`, true);
    }
  } finally {
    refreshButton.disabled = false;
    refreshButton.removeAttribute("aria-busy");
    refreshButton.innerHTML = '<span aria-hidden="true">↻</span> Check for updates';
  }
}

previousButton.addEventListener("click", () => turnPage(-1));
nextButton.addEventListener("click", () => turnPage(1));
refreshButton.addEventListener("click", () => checkForUpdates({ manual: true }));
document.getElementById("contents-button").addEventListener("click", () => contentsDialog.showModal());
document.getElementById("close-contents").addEventListener("click", () => contentsDialog.close());
contentsDialog.addEventListener("click", event => {
  if (event.target === contentsDialog) contentsDialog.close();
});
window.addEventListener("keydown", event => {
  if (contentsDialog.open) return;
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const tag = event.target?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || event.target?.isContentEditable) return;
  if (event.key === "ArrowRight" || event.key === "PageDown") {
    event.preventDefault();
    turnPage(1);
  } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
    event.preventDefault();
    turnPage(-1);
  } else if (event.key === "Home") {
    event.preventDefault();
    goToPage(0);
  } else if (event.key === "End" && bookData) {
    event.preventDefault();
    goToPage(bookData.pages.length - 1);
  }
});
window.addEventListener("resize", renderBook);
bookElement.addEventListener("touchstart", event => {
  touchStartX = event.changedTouches[0]?.clientX ?? null;
}, { passive: true });
bookElement.addEventListener("touchend", event => {
  if (touchStartX === null) return;
  const delta = event.changedTouches[0].clientX - touchStartX;
  touchStartX = null;
  if (Math.abs(delta) > 55) turnPage(delta < 0 ? 1 : -1);
}, { passive: true });
window.addEventListener("online", () => {
  document.getElementById("offline-note").hidden = true;
  checkForUpdates();
});
window.addEventListener("offline", () => {
  document.getElementById("offline-note").hidden = false;
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) checkForUpdates();
});
window.setInterval(() => {
  if (!document.hidden) checkForUpdates();
}, NEWS_REFRESH_INTERVAL);

window.addEventListener("beforeinstallprompt", event => {
  event.preventDefault();
  pendingInstall = event;
  installButton.hidden = false;
});
installButton.addEventListener("click", async () => {
  if (!pendingInstall) return;
  pendingInstall.prompt();
  await pendingInstall.userChoice;
  pendingInstall = null;
  installButton.hidden = true;
});
window.addEventListener("appinstalled", () => {
  pendingInstall = null;
  installButton.hidden = true;
  document.getElementById("news-status").textContent = "The book is installed on this device";
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(error => {
      showNotice(`Offline reading could not be enabled: ${error.message}`, true);
    });
  });
}

checkForUpdates();
