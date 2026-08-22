"use strict";

var _require = require("./errors.js"),
  XTInternalError = _require.XTInternalError;
function emptyFun() {}
function identity(i) {
  return i;
}
module.exports = function (module) {
  var defaults = {
    on: emptyFun,
    set: emptyFun,
    getFileType: emptyFun,
    optionsTransformer: identity,
    preparse: identity,
    matchers: function matchers() {
      return [];
    },
    parse: emptyFun,
    getTraits: emptyFun,
    postparse: identity,
    errorsTransformer: identity,
    preResolve: emptyFun,
    resolve: emptyFun,
    getRenderedMap: identity,
    render: emptyFun,
    nullGetter: emptyFun,
    postrender: identity
  };
  if (Object.keys(defaults).every(function (key) {
    return !module[key];
  })) {
    var err = new XTInternalError("This module cannot be wrapped, because it doesn't define any of the necessary functions");
    err.properties = {
      id: "module_cannot_be_wrapped",
      explanation: "This module cannot be wrapped, because it doesn't define any of the necessary functions"
    };
    throw err;
  }
  for (var key in defaults) {
    module[key] || (module[key] = defaults[key]);
  }
  return module;
};