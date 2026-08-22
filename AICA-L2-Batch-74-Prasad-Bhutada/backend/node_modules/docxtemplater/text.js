"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _regenerator() { /*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE */ var e, t, r = "function" == typeof Symbol ? Symbol : {}, n = r.iterator || "@@iterator", o = r.toStringTag || "@@toStringTag"; function i(r, n, o, i) { var c = n && n.prototype instanceof Generator ? n : Generator, u = Object.create(c.prototype); return _regeneratorDefine2(u, "_invoke", function (r, n, o) { var i, c, u, f = 0, p = o || [], y = !1, G = { p: 0, n: 0, v: e, a: d, f: d.bind(e, 4), d: function d(t, r) { return i = t, c = 0, u = e, G.n = r, a; } }; function d(r, n) { for (c = r, u = n, t = 0; !y && f && !o && t < p.length; t++) { var o, i = p[t], d = G.p, l = i[2]; r > 3 ? (o = l === n) && (u = i[(c = i[4]) ? 5 : (c = 3, 3)], i[4] = i[5] = e) : i[0] <= d && ((o = r < 2 && d < i[1]) ? (c = 0, G.v = n, G.n = i[1]) : d < l && (o = r < 3 || i[0] > n || n > l) && (i[4] = r, i[5] = n, G.n = l, c = 0)); } if (o || r > 1) return a; throw y = !0, n; } return function (o, p, l) { if (f > 1) throw TypeError("Generator is already running"); for (y && 1 === p && d(p, l), c = p, u = l; (t = c < 2 ? e : u) || !y;) { i || (c ? c < 3 ? (c > 1 && (G.n = -1), d(c, u)) : G.n = u : G.v = u); try { if (f = 2, i) { if (c || (o = "next"), t = i[o]) { if (!(t = t.call(i, u))) throw TypeError("iterator result is not an object"); if (!t.done) return t; u = t.value, c < 2 && (c = 0); } else 1 === c && (t = i["return"]) && t.call(i), c < 2 && (u = TypeError("The iterator does not provide a '" + o + "' method"), c = 1); i = e; } else if ((t = (y = G.n < 0) ? u : r.call(n, G)) !== a) break; } catch (t) { i = e, c = 1, u = t; } finally { f = 1; } } return { value: t, done: y }; }; }(r, o, i), !0), u; } var a = {}; function Generator() {} function GeneratorFunction() {} function GeneratorFunctionPrototype() {} t = Object.getPrototypeOf; var c = [][n] ? t(t([][n]())) : (_regeneratorDefine2(t = {}, n, function () { return this; }), t), u = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(c); function f(e) { return Object.setPrototypeOf ? Object.setPrototypeOf(e, GeneratorFunctionPrototype) : (e.__proto__ = GeneratorFunctionPrototype, _regeneratorDefine2(e, o, "GeneratorFunction")), e.prototype = Object.create(u), e; } return GeneratorFunction.prototype = GeneratorFunctionPrototype, _regeneratorDefine2(u, "constructor", GeneratorFunctionPrototype), _regeneratorDefine2(GeneratorFunctionPrototype, "constructor", GeneratorFunction), GeneratorFunction.displayName = "GeneratorFunction", _regeneratorDefine2(GeneratorFunctionPrototype, o, "GeneratorFunction"), _regeneratorDefine2(u), _regeneratorDefine2(u, o, "Generator"), _regeneratorDefine2(u, n, function () { return this; }), _regeneratorDefine2(u, "toString", function () { return "[object Generator]"; }), (_regenerator = function _regenerator() { return { w: i, m: f }; })(); }
function _regeneratorDefine2(e, r, n, t) { var i = Object.defineProperty; try { i({}, "", {}); } catch (e) { i = 0; } _regeneratorDefine2 = function _regeneratorDefine(e, r, n, t) { function o(r, n) { _regeneratorDefine2(e, r, function (e) { return this._invoke(r, n, e); }); } r ? i ? i(e, r, { value: n, enumerable: !t, configurable: !t, writable: !t }) : e[r] = n : (o("next", 0), o("throw", 1), o("return", 2)); }, _regeneratorDefine2(e, r, n, t); }
function asyncGeneratorStep(n, t, e, r, o, a, c) { try { var i = n[a](c), u = i.value; } catch (n) { return void e(n); } i.done ? t(u) : Promise.resolve(u).then(r, o); }
function _asyncToGenerator(n) { return function () { var t = this, e = arguments; return new Promise(function (r, o) { var a = n.apply(t, e); function _next(n) { asyncGeneratorStep(a, r, o, _next, _throw, "next", n); } function _throw(n) { asyncGeneratorStep(a, r, o, _next, _throw, "throw", n); } _next(void 0); }); }; }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var Lexer = require("./js/lexer.js");
var Parser = require("./js/parser.js");
var createScope = require("./js/scope-manager.js");
var utf8decode = require("./js/uintarray-to-string.js");
var _require = require("./js/doc-utils.js"),
  getDefaults = _require.getDefaults,
  pushArray = _require.pushArray;
var _require2 = require("./js/errors.js"),
  throwMultiError = _require2.throwMultiError;
var renderModule = require("./js/modules/render.js");
var loopModule = require("./js/modules/loop.js");
var expandPairTrait = require("./js/modules/expand-pair-trait.js");
var XmlTemplater = require("./js/xml-templater.js");
function TxtTemplater(text) {
  var options = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  var filePath = "text";
  var xmltOptions = {
    fileType: "text",
    modules: []
  };
  var xmlt = new XmlTemplater(text, xmltOptions);
  this.fileTypeConfig = xmlt.fileTypeConfig = options.fileTypeConfig = {
    droppedTagsInsidePlaceholder: [],
    expandTags: []
  };
  var defaults = getDefaults();
  for (var key in defaults) {
    var defaultValue = defaults[key];
    xmlt[key] = options[key] = options[key] != null ? options[key] : defaultValue;
  }
  xmlt.modules = [loopModule(), expandPairTrait(), renderModule()];
  for (var _i2 = 0, _xmlt$modules2 = xmlt.modules; _i2 < _xmlt$modules2.length; _i2++) {
    var _module = _xmlt$modules2[_i2];
    _module.optionsTransformer(options, _objectSpread(_objectSpread({
      fileTypeConfig: xmlt.fileTypeConfig
    }, xmltOptions), {}, {
      parser: xmlt.parser,
      options: xmlt
    }));
  }
  xmlt.allErrors = [];
  // Fake XML parsing : surround the text with an empty tag of type text: true
  xmlt.xmllexed = [{
    type: "tag",
    position: "start",
    value: "",
    text: true
  }, {
    type: "content",
    value: text
  }, {
    type: "tag",
    position: "end",
    value: ""
  }];
  xmlt.setModules({
    inspect: {
      filePath: filePath,
      xmllexed: xmlt.xmllexed
    }
  });
  var _Lexer$parse = Lexer.parse(xmlt.xmllexed, xmlt.delimiters, xmlt.syntax, xmlt.fileType),
    lexed = _Lexer$parse.lexed,
    lexerErrors = _Lexer$parse.errors;
  pushArray(xmlt.allErrors, lexerErrors);
  xmlt.lexed = lexed;
  xmlt.setModules({
    inspect: {
      filePath: filePath,
      lexed: xmlt.lexed
    }
  });
  xmlt.lexed = Parser.preparse(xmlt.lexed, xmlt.modules, xmlt.getOptions());
  xmlt.parse();
  if (xmlt.allErrors.length > 0) {
    throwMultiError(xmlt.allErrors);
  }
  this.renderAsync = /*#__PURE__*/function () {
    var _ref = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee(tags) {
      return _regenerator().w(function (_context) {
        while (1) switch (_context.n) {
          case 0:
            xmlt.scopeManager = createScope({
              tags: tags,
              parser: xmlt.parser
            });
            _context.n = 1;
            return xmlt.resolveTags(tags);
          case 1:
            xmlt.render();
            if (xmlt.allErrors.length > 0) {
              throwMultiError(xmlt.allErrors);
            }
            return _context.a(2, utf8decode(xmlt.content));
        }
      }, _callee);
    }));
    return function (_x) {
      return _ref.apply(this, arguments);
    };
  }();
  this.render = function (tags) {
    xmlt.scopeManager = createScope({
      tags: tags,
      parser: xmlt.parser
    });
    xmlt.render();
    if (xmlt.allErrors.length > 0) {
      throwMultiError(xmlt.allErrors);
    }
    return utf8decode(xmlt.content);
  };
  return this;
}
module.exports = TxtTemplater;
module.exports["default"] = TxtTemplater;