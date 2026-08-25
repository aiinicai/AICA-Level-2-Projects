"use strict";

var _require = require("./content-types.js"),
  settingsContentType = _require.settingsContentType;
module.exports = {
  name: "ProofStateModule",
  on: function on(eventName) {
    if (eventName === "attached") {
      this.attached = false;
    }
  },
  postparse: function postparse(postparsed, _ref) {
    var contentType = _ref.contentType;
    if (contentType !== settingsContentType) {
      return null;
    }
    var result = [];
    for (var _i2 = 0; _i2 < postparsed.length; _i2++) {
      var part = postparsed[_i2];
      if (part.type === "tag" && part.tag === "w:proofState") {
        result.push({
          type: "content",
          value: ""
        });
      } else {
        result.push(part);
      }
    }
    return result;
  }
};