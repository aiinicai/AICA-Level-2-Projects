/* What HTMX and Alpine do not cover. Build Prompt v2 §8.7.
 *
 * Autosave itself is HTMX (`hx-post`, `hx-trigger`, `hx-select`) and the save
 * indicator is Alpine, both declared in workspace.html. What is left is two
 * behaviours neither library provides: Ctrl+S to save the focused field, and
 * a warning if the window is closed mid-save.
 *
 * Everything here is an enhancement. With JavaScript off, every control is
 * still a real <form> with a real submit button, which is what makes the
 * Phase 6 exit test pass without any of this running.
 */
(function () {
  "use strict";

  function saving() {
    return document.querySelector(".save-status.saving") !== null;
  }

  document.addEventListener("keydown", function (event) {
    if (!(event.ctrlKey || event.metaKey) || event.key !== "s") return;
    var active = document.activeElement;
    var form = active && active.closest ? active.closest("form.autosave") : null;
    if (!form) return;
    event.preventDefault();
    // Let HTMX do the request so the swap and the indicator behave the same
    // way they do on a blur.
    if (window.htmx) window.htmx.trigger(form, "change");
    else form.submit();
  });

  window.addEventListener("beforeunload", function (event) {
    if (!saving()) return;
    event.preventDefault();
    event.returnValue = "";
  });
})();
