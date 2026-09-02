/*
 * FinSight — form loading-state enhancement (Stage 14 section 16).
 *
 * "Do not make the user wonder whether the application is frozen."
 * FinSight's screens are plain synchronous POSTs (no fetch/AJAX
 * anywhere in this app — offline-first, dependency-free, per the
 * existing architecture), so the only moment a user could wonder
 * whether something is frozen is between clicking Submit and the next
 * page load. This script only swaps a submit button's own label to a
 * data-loading-text value and disables it, so a double-click can't
 * double-submit and the button visibly acknowledges the click. It does
 * not intercept, delay, or fake anything — the real page navigation
 * that follows is what actually resolves the "is it frozen?" question.
 *
 * Opt-in only: a form/button pair does nothing unless the submit
 * button explicitly carries data-loading-text, so this never changes
 * behavior on a button that hasn't been given wording for it.
 */
(function () {
  "use strict";

  function init() {
    document.querySelectorAll("form").forEach(function (form) {
      form.addEventListener("submit", function () {
        var btn = form.querySelector("button[type=submit][data-loading-text], button[data-loading-text]");
        if (!btn) return;
        // Let the browser serialize the form with the button's current
        // label before we relabel it; disabling after a microtask avoids
        // some browsers omitting a disabled button's value from the
        // submission, though FinSight's buttons carry no name/value.
        window.setTimeout(function () {
          btn.textContent = btn.getAttribute("data-loading-text");
          btn.disabled = true;
        }, 0);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
