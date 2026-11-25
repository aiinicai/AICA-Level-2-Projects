// Small glue code. No inline scripts are used, so the Content-Security-Policy can stay strict.
document.addEventListener("htmx:afterSwap", function (e) {
  if (e.detail.target && e.detail.target.id === "modal-body" && window.bootstrap) {
    bootstrap.Modal.getOrCreateInstance(document.getElementById("modal")).show();
  }
});
document.addEventListener("htmx:responseError", function (e) {
  alert("The server could not complete the request (" + e.detail.xhr.status + "). Reload the page and try again.");
});
// Ask before submitting forms marked data-confirm (exclude, revoke...). Works for normal and HTMX forms.
document.addEventListener("submit", function (e) {
  var msg = e.target.getAttribute && e.target.getAttribute("data-confirm");
  if (msg && !window.confirm(msg)) { e.preventDefault(); e.stopImmediatePropagation(); }
}, true);
// Forms marked data-busy take a while (e.g. Excel export with the formula check): stop double clicks.
document.addEventListener("submit", function (e) {
  var busy = e.target.getAttribute && e.target.getAttribute("data-busy");
  if (!busy || e.defaultPrevented) { return; }
  e.target.querySelectorAll("button").forEach(function (b) { b.disabled = true; b.textContent = busy; });
});
