"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function safeStringify(obj) {
  var cache = [];
  return JSON.stringify(obj, function (key, value) {
    if (_typeof(value) === "object" && value !== null) {
      if (cache.indexOf(value) !== -1) {
        // Circular reference found
        return;
      }
      cache.push(value);
    }
    return value;
  }, null);
}
module.exports = safeStringify;