/*
 * FinSight — multi-file Data Upload convenience (post-Stage-17 fix).
 *
 * The Upload screen's file picker accepts several files in one action
 * (a plain `<input type="file" multiple>`), but each file still needs
 * its own Data Type — a single global selector can't represent that
 * once more than one file is chosen. This script renders a small
 * "File Name / File Type" row per selected file, each with its own
 * `<select name="file_type__<index>">`, matching the order the browser
 * reports the chosen files in — the same order `request.files.getlist
 * ("file")` reads them back in on the server, so index N here is
 * always index N there.
 *
 * Opt-in / progressive-enhancement in spirit: with JavaScript
 * disabled, the file input still works for a single file (see the
 * <noscript> hint on the page), it just can't offer a per-file type
 * picker — the server-side upload logic itself does not depend on
 * this script running at all.
 *
 * No fetch/AJAX — this only rearranges what's on the page before the
 * user submits the same plain multipart POST the rest of FinSight
 * already uses (see forms.js's own docstring for why that matters
 * here).
 */
(function () {
  "use strict";

  function init() {
    var input = document.getElementById("file");
    var listWrap = document.getElementById("fs-upload-file-list");
    var listBody = document.getElementById("fs-upload-file-list-body");
    var optionsTemplate = document.getElementById("fs-file-type-options-template");
    if (!input || !listWrap || !listBody || !optionsTemplate) return;

    input.addEventListener("change", function () {
      listBody.innerHTML = "";

      var files = input.files || [];
      if (files.length === 0) {
        listWrap.hidden = true;
        return;
      }

      for (var i = 0; i < files.length; i++) {
        var row = document.createElement("tr");

        var nameCell = document.createElement("td");
        nameCell.textContent = files[i].name;
        row.appendChild(nameCell);

        var typeCell = document.createElement("td");
        var select = document.createElement("select");
        select.name = "file_type__" + i;
        select.required = true;
        select.appendChild(optionsTemplate.content.cloneNode(true));
        typeCell.appendChild(select);
        row.appendChild(typeCell);

        listBody.appendChild(row);
      }

      listWrap.hidden = false;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
