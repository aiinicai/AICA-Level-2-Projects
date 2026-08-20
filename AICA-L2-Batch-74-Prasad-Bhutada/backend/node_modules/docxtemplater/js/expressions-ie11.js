"use strict";

var expressions = require("./expressions.js");
var exportedValue = expressions.configure({
  useProxy: false
});
exportedValue.configure = function () {
  var config = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
  config.useProxy = false;
  return expressions.configure(config);
};
exportedValue.filters = expressions.filters;
exportedValue.compile = expressions.compile;
exportedValue.Parser = expressions.Parser;
exportedValue.Lexer = expressions.Lexer;
module.exports = exportedValue;