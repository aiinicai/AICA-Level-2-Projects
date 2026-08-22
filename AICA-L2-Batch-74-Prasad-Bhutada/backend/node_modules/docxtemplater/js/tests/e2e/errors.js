"use strict";

function _regenerator() { /*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE */ var e, t, r = "function" == typeof Symbol ? Symbol : {}, n = r.iterator || "@@iterator", o = r.toStringTag || "@@toStringTag"; function i(r, n, o, i) { var c = n && n.prototype instanceof Generator ? n : Generator, u = Object.create(c.prototype); return _regeneratorDefine2(u, "_invoke", function (r, n, o) { var i, c, u, f = 0, p = o || [], y = !1, G = { p: 0, n: 0, v: e, a: d, f: d.bind(e, 4), d: function d(t, r) { return i = t, c = 0, u = e, G.n = r, a; } }; function d(r, n) { for (c = r, u = n, t = 0; !y && f && !o && t < p.length; t++) { var o, i = p[t], d = G.p, l = i[2]; r > 3 ? (o = l === n) && (u = i[(c = i[4]) ? 5 : (c = 3, 3)], i[4] = i[5] = e) : i[0] <= d && ((o = r < 2 && d < i[1]) ? (c = 0, G.v = n, G.n = i[1]) : d < l && (o = r < 3 || i[0] > n || n > l) && (i[4] = r, i[5] = n, G.n = l, c = 0)); } if (o || r > 1) return a; throw y = !0, n; } return function (o, p, l) { if (f > 1) throw TypeError("Generator is already running"); for (y && 1 === p && d(p, l), c = p, u = l; (t = c < 2 ? e : u) || !y;) { i || (c ? c < 3 ? (c > 1 && (G.n = -1), d(c, u)) : G.n = u : G.v = u); try { if (f = 2, i) { if (c || (o = "next"), t = i[o]) { if (!(t = t.call(i, u))) throw TypeError("iterator result is not an object"); if (!t.done) return t; u = t.value, c < 2 && (c = 0); } else 1 === c && (t = i["return"]) && t.call(i), c < 2 && (u = TypeError("The iterator does not provide a '" + o + "' method"), c = 1); i = e; } else if ((t = (y = G.n < 0) ? u : r.call(n, G)) !== a) break; } catch (t) { i = e, c = 1, u = t; } finally { f = 1; } } return { value: t, done: y }; }; }(r, o, i), !0), u; } var a = {}; function Generator() {} function GeneratorFunction() {} function GeneratorFunctionPrototype() {} t = Object.getPrototypeOf; var c = [][n] ? t(t([][n]())) : (_regeneratorDefine2(t = {}, n, function () { return this; }), t), u = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(c); function f(e) { return Object.setPrototypeOf ? Object.setPrototypeOf(e, GeneratorFunctionPrototype) : (e.__proto__ = GeneratorFunctionPrototype, _regeneratorDefine2(e, o, "GeneratorFunction")), e.prototype = Object.create(u), e; } return GeneratorFunction.prototype = GeneratorFunctionPrototype, _regeneratorDefine2(u, "constructor", GeneratorFunctionPrototype), _regeneratorDefine2(GeneratorFunctionPrototype, "constructor", GeneratorFunction), GeneratorFunction.displayName = "GeneratorFunction", _regeneratorDefine2(GeneratorFunctionPrototype, o, "GeneratorFunction"), _regeneratorDefine2(u), _regeneratorDefine2(u, o, "Generator"), _regeneratorDefine2(u, n, function () { return this; }), _regeneratorDefine2(u, "toString", function () { return "[object Generator]"; }), (_regenerator = function _regenerator() { return { w: i, m: f }; })(); }
function _regeneratorDefine2(e, r, n, t) { var i = Object.defineProperty; try { i({}, "", {}); } catch (e) { i = 0; } _regeneratorDefine2 = function _regeneratorDefine(e, r, n, t) { function o(r, n) { _regeneratorDefine2(e, r, function (e) { return this._invoke(r, n, e); }); } r ? i ? i(e, r, { value: n, enumerable: !t, configurable: !t, writable: !t }) : e[r] = n : (o("next", 0), o("throw", 1), o("return", 2)); }, _regeneratorDefine2(e, r, n, t); }
function asyncGeneratorStep(n, t, e, r, o, a, c) { try { var i = n[a](c), u = i.value; } catch (n) { return void e(n); } i.done ? t(u) : Promise.resolve(u).then(r, o); }
function _asyncToGenerator(n) { return function () { var t = this, e = arguments; return new Promise(function (r, o) { var a = n.apply(t, e); function _next(n) { asyncGeneratorStep(a, r, o, _next, _throw, "next", n); } function _throw(n) { asyncGeneratorStep(a, r, o, _next, _throw, "throw", n); } _next(void 0); }); }; }
var Errors = require("../../errors.js");
var _require = require("../utils.js"),
  loadFile = _require.loadFile,
  rejectSoon = _require.rejectSoon,
  expect = _require.expect,
  loadDocumentV4 = _require.loadDocumentV4,
  createDocV4 = _require.createDocV4,
  makeDocxV4 = _require.makeDocxV4,
  wrapMultiError = _require.wrapMultiError,
  expectToThrow = _require.expectToThrow,
  expectToThrowSnapshot = _require.expectToThrowSnapshot,
  expectToThrowAsync = _require.expectToThrowAsync,
  captureLogs = _require.captureLogs;
var expressionParser = require("../../expressions.js");
var xmlPrettify = require("../xml-prettify.js");
describe("Compilation errors", function () {
  it("should fail when parsing invalid xml (1)", function () {
    var content = "<w:t";
    var expectedError = {
      name: "TemplateError",
      message: "An XML file has invalid xml",
      properties: {
        content: content,
        offset: 0,
        id: "file_has_invalid_xml"
      }
    };
    expectToThrow(function () {
      return makeDocxV4(content);
    }, Errors.XTTemplateError, expectedError);
  });
  it("should fail when parsing invalid xml (2)", function () {
    var content = "<w:t>Foobar </w:t><w:t>Foobar </w:t><w:t>Foobar </w:t> <w:t John Jane Mary Doe</w:t>";
    var expectedError = {
      name: "TemplateError",
      message: "An XML file has invalid xml",
      properties: {
        content: content,
        offset: 55,
        id: "file_has_invalid_xml"
      }
    };
    expectToThrow(function () {
      return makeDocxV4(content);
    }, Errors.XTTemplateError, expectedError);
  });
  it("should fail when tag unclosed at end of document", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Unclosed tag",
      properties: {
        context: "{unclosedtag my text",
        file: "word/document.xml",
        id: "unclosed_tag",
        xtag: "unclosedtag",
        offset: 0
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{unclosedtag my text</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should be possible to not log error message", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Unclosed tag",
      properties: {
        context: "{unclosedtag my text",
        file: "word/document.xml",
        id: "unclosed_tag",
        xtag: "unclosedtag",
        offset: 0
      }
    };
    var capture = captureLogs();
    expectToThrow(function () {
      return makeDocxV4("<w:t>{unclosedtag my text</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
    capture.stop();
    var logs = capture.logs();
    expect(logs.length).to.equal(0);
  });
  it("should fail when tag unclosed", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Unclosed tag",
      properties: {
        file: "word/document.xml",
        id: "unclosed_tag",
        context: "{user ",
        xtag: "user",
        offset: 0
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{user {name}</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should fail when tag unopened", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Unopened tag",
      properties: {
        file: "word/document.xml",
        id: "unopened_tag",
        context: "foobar",
        offset: 6,
        xtag: "foobar"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foobar}age</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should fail when closing {#users} with {/foo}", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Closing tag does not match opening tag",
      properties: {
        file: "word/document.xml",
        id: "closing_tag_does_not_match_opening_tag",
        openingtag: "users",
        closingtag: "foo"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{#users}User {name}{/foo}</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should fail when closing an unopened loop", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Unopened loop",
      properties: {
        file: "word/document.xml",
        id: "unopened_loop",
        xtag: "loop",
        offset: 0
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{/loop} {foobar}</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should fail when a loop is never closed", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Unclosed loop",
      properties: {
        file: "word/document.xml",
        id: "unclosed_loop",
        xtag: "loop",
        offset: 0
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{#loop} {foobar}</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should fail early when a loop closes the wrong loop", function () {
    expectToThrowSnapshot(function () {
      return makeDocxV4("<w:t>{#loop1}{#loop2}{/loop3}{/loop3}{/loop2}{/loop1}</w:t>", {
        errorLogging: false
      });
    });
  });
  it("should fail when rawtag is not in paragraph", function () {
    expectToThrowSnapshot(function () {
      return makeDocxV4("<w:t>{@myrawtag}</w:t>", {
        errorLogging: false
      });
    });
  });
  it("should fail when rawtag is in table without paragraph", function () {
    expectToThrowSnapshot(function () {
      return makeDocxV4("<w:tbl><w:t>{@myrawtag}</w:t></w:p></w:tbl>", {
        errorLogging: false
      });
    });
  });
  it("should fail when rawtag is not only text in paragraph", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Raw tag should be the only text in paragraph",
      properties: {
        file: "word/document.xml",
        id: "raw_xml_tag_should_be_only_text_in_paragraph",
        xtag: "myrawtag",
        offset: 1,
        paragraphPartsLength: 7
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:p><w:t> {@myrawtag}</w:t><w:t>foobar</w:t></w:p>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should count 3 errors when having rawxml and two other errors", function () {
    expectToThrowSnapshot(function () {
      return makeDocxV4("<w:p><w:r><w:t>foo} {@bang} bar}</w:t></w:r></w:p>", {
        errorLogging: false
      });
    });
  });
  it("should fail when customparser fails to compile", function () {
    var expectedError = {
      name: "ScopeParserError",
      message: "Scope parser compilation failed",
      properties: {
        file: "word/document.xml",
        id: "scopeparser_compilation_failed",
        xtag: "name++",
        rootError: {
          message: "[$parse:ueoe] Unexpected end of expression: name++\nhttp://errors.angularjs.org/\"NG_VERSION_FULL\"/$parse/ueoe?p0=name%2B%2B"
        }
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{name++}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
});
describe("Runtime errors", function () {
  it("should fail when customparser fails to execute", function () {
    function errorParser() {
      return {
        get: function get() {
          throw new Error("foo bar");
        }
      };
    }
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_execution_failed",
            xtag: "name|upper",
            offset: 1,
            rootError: {
              message: "foo bar"
            }
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t> {name|upper}</w:t>", {
        parser: errorParser,
        errorLogging: false
      }).render();
    }, Errors.XTTemplateError, expectedError);
  });
  it("should be possible to log the error", function () {
    var errorStringified = "";
    function errorParser() {
      return {
        get: function get() {
          throw new Error("foo bar 6aaef652-8525-4442-b9b8-5ab942b2c476");
        }
      };
    }
    function replaceErrors(key, value) {
      if (value instanceof Error) {
        var error = {};
        for (var _i2 = 0, _Object$getOwnPropert2 = Object.getOwnPropertyNames(value); _i2 < _Object$getOwnPropert2.length; _i2++) {
          var _key = _Object$getOwnPropert2[_i2];
          error[_key] = value[_key];
        }
        return error;
      }
      return value;
    }
    var capture = captureLogs();
    try {
      makeDocxV4("<w:t> {name|upper}</w:t>", {
        parser: errorParser
      }).render();
      capture.stop();
    } catch (e) {
      capture.stop();
      errorStringified = JSON.stringify(e, replaceErrors, 2);
    }
    expect(errorStringified).to.contain("foo bar 6aaef652-8525-4442-b9b8-5ab942b2c476");
  });
  it("should fail with multi-error when customparser fails to execute on multiple raw tags", function () {
    var count = 0;
    function errorParser() {
      return {
        get: function get() {
          count++;
          throw new Error("foo ".concat(count));
        }
      };
    }
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            id: "scopeparser_execution_failed",
            file: "word/document.xml",
            xtag: "raw|isfalse",
            rootError: {
              message: "foo 1"
            },
            offset: 0
          }
        }, {
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_execution_failed",
            xtag: "raw|istrue",
            rootError: {
              message: "foo 2"
            },
            offset: 14
          }
        }],
        id: "multi_error"
      }
    };
    var doc = makeDocxV4("\n\t\t<w:p><w:r><w:t>{@raw|isfalse}</w:t></w:r></w:p>\n\t\t<w:p><w:r><w:t>{@raw|istrue}</w:t></w:r></w:p>\n\t\t", {
      parser: errorParser,
      errorLogging: false
    });
    expectToThrow(function () {
      return doc.render();
    }, Errors.XTTemplateError, expectedError);
  });
  it("should fail if having error in function", function () {
    expectToThrow(function () {
      return makeDocxV4("<w:p><w:r><w:t>{fn}</w:t></w:r></w:p>", {
        errorLogging: false
      }).render({
        fn: function fn() {
          throw new Error("foobar");
        }
      });
    }, Errors.XTTemplateError, {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            id: "scopeparser_execution_failed",
            file: "word/document.xml",
            xtag: "fn",
            scope: {},
            rootError: {
              message: "foobar"
            },
            offset: 0
          }
        }],
        id: "multi_error"
      }
    });
  });
  it("should fail if having error in function async", function () {
    expectToThrowAsync(function () {
      return makeDocxV4("<w:p><w:r><w:t>{fn}</w:t></w:r></w:p>", {
        errorLogging: false
      }).renderAsync({
        fn: function fn() {
          throw new Error("foobar");
        }
      });
    }, Errors.XTTemplateError, {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            id: "scopeparser_execution_failed",
            file: "word/document.xml",
            xtag: "fn",
            scope: {},
            rootError: {
              message: "foobar"
            },
            offset: 0
          }
        }],
        id: "multi_error"
      }
    });
  });
});
describe("Internal errors", function () {
  it("should fail if using odt format", function (done) {
    var expectedError = {
      name: "InternalError",
      message: 'The filetype "odt" is not handled by Docxtemplater',
      properties: {
        id: "filetype_not_handled",
        fileType: "odt"
      }
    };
    loadFile("test.odt", function (e, name, buffer) {
      expectToThrow(function () {
        return loadDocumentV4(name, buffer);
      }, Errors.XTInternalError, expectedError);
      done();
    });
  });
  it("should fail if using zip file and show list of files", function (done) {
    var expectedError = {
      name: "InternalError",
      message: "The filetype for this file could not be identified, is this file corrupted ? Zip file contains : world.txt,xxx.log",
      properties: {
        id: "filetype_not_identified"
      }
    };
    loadFile("simple-zip.zip", function (e, name, buffer) {
      expectToThrow(function () {
        return loadDocumentV4(name, buffer);
      }, Errors.XTInternalError, expectedError);
      done();
    });
  });
  it("should fail if using empty zip file and show it", function (done) {
    var expectedError = {
      name: "InternalError",
      message: "The filetype for this file could not be identified, is this file corrupted ? Empty zip file",
      properties: {
        id: "filetype_not_identified"
      }
    };
    loadFile("empty.zip", function (e, name, buffer) {
      expectToThrow(function () {
        return loadDocumentV4(name, buffer);
      }, Errors.XTInternalError, expectedError);
      done();
    });
  });
});
describe("Multi errors", function () {
  it("should work with multiple errors simple", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        id: "multi_error",
        errors: [{
          message: "Unopened tag",
          name: "TemplateError",
          properties: {
            offset: 3,
            context: "foo",
            id: "unopened_tag",
            xtag: "foo",
            file: "word/document.xml"
          }
        }, {
          message: "Unclosed tag",
          name: "TemplateError",
          properties: {
            offset: 11,
            context: "{user, my age is ",
            id: "unclosed_tag",
            xtag: "user,",
            file: "word/document.xml"
          }
        }]
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foo} Hello {user, my age is {bar}</w:t>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with multiple errors complex", function () {
    var content = "<w:t>foo}\n\t\tHello {user, my age is {bar}\n\t\t\tHi bang}, my name is {user2}\n\t\t\tHey {user}, my age is {bar}\n\t\t\tHola {bang}, my name is {user2}\n\t\t\t{user, my age is {bar\n\t\t\t\t</w:t>".replace(/\t/g, "").split("\n").join("!");
    expectToThrowSnapshot(function () {
      return makeDocxV4(content, {
        errorLogging: false
      });
    });
  });
  it("should work with wrongly nested loops", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: "Unopened loop",
          properties: {
            file: "word/document.xml",
            id: "unopened_loop",
            xtag: "companies"
          }
        }, {
          name: "TemplateError",
          message: "Unclosed loop",
          properties: {
            file: "word/document.xml",
            id: "unclosed_loop",
            xtag: "companies"
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("\n\t\t<w:t>\n\t\t\t{#users}.........{/companies}\n\t\t\t{#companies}.....{/users}\n\t\t</w:t>\n\t\t", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with loops", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: "Closing tag does not match opening tag",
          properties: {
            file: "word/document.xml",
            id: "closing_tag_does_not_match_opening_tag",
            openingtag: "users",
            closingtag: "foo"
          }
        }, {
          name: "TemplateError",
          message: "Closing tag does not match opening tag",
          properties: {
            file: "word/document.xml",
            id: "closing_tag_does_not_match_opening_tag",
            openingtag: "bang",
            closingtag: "baz"
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("\n\t\t\t\t\t<w:t>{#users}User name{/foo}\n\t\t\t\t\t{#bang}User name{/baz}\n\t\t\t\t\t</w:t>\n\t\t\t\t\t", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with loops unopened", function () {
    expectToThrowSnapshot(function () {
      return makeDocxV4("<w:t>{/loop} {#users}User name{/foo}\n\t\t\t\t{#bang}User name{/baz}\n\t\t\t\t{/fff}\n\t\t\t\t{#yum}\n\t\t\t\t</w:t>\n\t\t\t\t", {
        errorLogging: false
      });
    });
  });
  it("should fail when having multiple rawtags without a surrounding paragraph", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: "Raw tag not in paragraph",
          properties: {
            file: "word/document.xml",
            id: "raw_tag_outerxml_invalid",
            xtag: "first",
            rootError: {
              message: 'No tag "w:p" was found at the left'
            },
            postparsedLength: 9,
            expandTo: "w:p",
            offset: 0,
            index: 1
          }
        }, {
          name: "TemplateError",
          message: "Raw tag should be the only text in paragraph",
          properties: {
            file: "word/document.xml",
            id: "raw_xml_tag_should_be_only_text_in_paragraph",
            paragraphPartsLength: 4,
            xtag: "second",
            offset: 11
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{@first}</w:t><w:p><w:t>foo{@second}</w:t></w:p>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should fail when customparser fails to compile", function () {
    var expectedError = {
      message: "Multi error",
      name: "TemplateError",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser compilation failed",
          properties: {
            file: "word/document.xml",
            offset: 0,
            id: "scopeparser_compilation_failed",
            xtag: "name++",
            rootError: {
              message: "[$parse:ueoe] Unexpected end of expression: name++\nhttp://errors.angularjs.org/\"NG_VERSION_FULL\"/$parse/ueoe?p0=name%2B%2B"
            }
          }
        }, {
          name: "ScopeParserError",
          message: "Scope parser compilation failed",
          properties: {
            file: "word/document.xml",
            offset: 9,
            id: "scopeparser_compilation_failed",
            xtag: "foo|||bang",
            rootError: {
              message: "[$parse:syntax] Syntax Error: Token '|' not a primary expression at column 6 of the expression [foo|||bang] starting at [|bang].\nhttp://errors.angularjs.org/\"NG_VERSION_FULL\"/$parse/syntax?p0=%7C&p1=not%20a%20primary%20expression&p2=6&p3=foo%7C%7C%7Cbang&p4=%7Cbang"
            }
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{name++} {foo|||bang}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should fail when customparser fails to compile 2", function () {
    var expectedError = {
      message: "Multi error",
      name: "TemplateError",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser compilation failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_compilation_failed",
            xtag: "name++",
            rootError: {
              message: "[$parse:ueoe] Unexpected end of expression: name++\nhttp://errors.angularjs.org/\"NG_VERSION_FULL\"/$parse/ueoe?p0=name%2B%2B"
            }
          }
        }, {
          name: "ScopeParserError",
          message: "Scope parser compilation failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_compilation_failed",
            xtag: "foo|||bang",
            rootError: {
              message: "[$parse:syntax] Syntax Error: Token '|' not a primary expression at column 6 of the expression [foo|||bang] starting at [|bang].\nhttp://errors.angularjs.org/\"NG_VERSION_FULL\"/$parse/syntax?p0=%7C&p1=not%20a%20primary%20expression&p2=6&p3=foo%7C%7C%7Cbang&p4=%7Cbang"
            }
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>{name++} {foo|||bang}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with lexer and customparser", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        id: "multi_error",
        errors: [{
          message: "Unopened tag",
          name: "TemplateError",
          properties: {
            context: "foo",
            id: "unopened_tag",
            xtag: "foo",
            file: "word/document.xml"
          }
        }, {
          message: "Scope parser compilation failed",
          name: "ScopeParserError",
          properties: {
            id: "scopeparser_compilation_failed",
            xtag: "name++",
            rootError: {
              message: "[$parse:ueoe] Unexpected end of expression: name++\nhttp://errors.angularjs.org/\"NG_VERSION_FULL\"/$parse/ueoe?p0=name%2B%2B"
            },
            file: "word/document.xml"
          }
        }]
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foo} Hello {name++}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with lexer and loop", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        id: "multi_error",
        errors: [{
          message: "Unopened tag",
          name: "TemplateError",
          properties: {
            context: "foo",
            id: "unopened_tag",
            xtag: "foo",
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Closing tag does not match opening tag",
          properties: {
            id: "closing_tag_does_not_match_opening_tag",
            openingtag: "users",
            closingtag: "bar",
            file: "word/document.xml"
          }
        }]
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foo} The users are {#users}{/bar}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with multiple errors", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        id: "multi_error",
        errors: [{
          message: "Unopened tag",
          name: "TemplateError",
          properties: {
            context: "foo",
            id: "unopened_tag",
            xtag: "foo",
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Closing tag does not match opening tag",
          properties: {
            id: "closing_tag_does_not_match_opening_tag",
            openingtag: "users",
            closingtag: "bar",
            offset: [19, 27],
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Raw tag not in paragraph",
          properties: {
            id: "raw_tag_outerxml_invalid",
            xtag: "bang",
            rootError: {
              message: 'No tag "w:p" was found at the left'
            },
            postparsedLength: 12,
            expandTo: "w:p",
            index: 9,
            file: "word/document.xml"
          }
        }]
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foo</w:t><w:t>} The users are {#users}{/bar} {@bang} </w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with multiple unclosed", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: "Unclosed tag",
          properties: {
            offset: 3,
            xtag: "city,",
            id: "unclosed_tag",
            context: "{city, ",
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Unclosed tag",
          properties: {
            offset: 10,
            xtag: "state",
            id: "unclosed_tag",
            context: "{state ",
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Unclosed tag",
          properties: {
            offset: 17,
            xtag: "zip",
            id: "unclosed_tag",
            context: "{zip ",
            file: "word/document.xml"
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foo</w:t>\n\t\t\t\t\t\t\t<w:t>{city, {state {zip </w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should work with multiple unopened", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: "Unopened tag",
          properties: {
            xtag: "city",
            id: "unopened_tag",
            context: "foo city",
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Unopened tag",
          properties: {
            xtag: "state",
            id: "unopened_tag",
            context: "}, state",
            file: "word/document.xml"
          }
        }, {
          name: "TemplateError",
          message: "Unopened tag",
          properties: {
            xtag: "zip",
            id: "unopened_tag",
            context: "} zip",
            file: "word/document.xml"
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:t>foo</w:t>\n\t\t\t\t\t\t\t<w:t> city}, state} zip}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should show an error when loop tag are badly used (xml open count !== xml close count)", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: 'The position of the loop tags "users" would produce invalid XML',
          properties: {
            xtag: "users",
            offset: [0, 17],
            id: "loop_position_invalid",
            file: "word/document.xml"
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:tbl>\n\t\t\t\t\t\t<w:tr>\n\t\t\t\t\t\t\t<w:tc>\n\t\t\t\t\t\t\t\t<w:p>\n\t\t\t\t\t\t\t\t\t<w:r>\n\t\t\t\t\t\t\t\t\t\t<w:t>{#users}</w:t>\n\t\t\t\t\t\t\t\t\t</w:r>\n\t\t\t\t\t\t\t\t\t<w:r>\n\t\t\t\t\t\t\t\t\t\t<w:t>test</w:t>\n\t\t\t\t\t\t\t\t\t</w:r>\n\t\t\t\t\t\t\t\t</w:p>\n\t\t\t\t\t\t\t</w:tc>\n\t\t\t\t\t\t\t<w:tc>\n\t\t\t\t\t\t\t\t<w:p>\n\t\t\t\t\t\t\t\t\t<w:r>\n\t\t\t\t\t\t\t\t\t\t<w:t>test2</w:t>\n\t\t\t\t\t\t\t\t\t</w:r>\n\t\t\t\t\t\t\t\t</w:p>\n\t\t\t\t\t\t\t</w:tc>\n\t\t\t\t\t\t</w:tr>\n\t\t\t\t\t</w:tbl>\n\t\t\t\t\t<w:p>\n\t\t\t\t\t\t<w:r>\n\t\t\t\t\t\t\t<w:t>{/users}</w:t>\n\t\t\t\t\t\t</w:r>\n\t\t\t\t\t</w:p>", {
        parser: expressionParser,
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
  it("should show an error when having table inside table", function () {
    expectToThrowSnapshot(function () {
      return createDocV4("error-table-tags.docx", {
        errorLogging: false
      });
    });
  });
  it("should show clean error message when using {{ with single delimiter", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "TemplateError",
          message: "Duplicate open tag, expected one open tag",
          properties: {
            context: "{{name",
            file: "word/document.xml",
            id: "duplicate_open_tag",
            offset: 0,
            xtag: "{{name"
          }
        }, {
          name: "TemplateError",
          message: "Duplicate close tag, expected one close tag",
          properties: {
            context: "name}}",
            file: "word/document.xml",
            id: "duplicate_close_tag",
            xtag: "name}}"
          }
        }],
        id: "multi_error"
      }
    };
    expectToThrow(function () {
      return makeDocxV4("<w:p><w:r><w:t>{{name}}</w:t></w:r></w:p>", {
        errorLogging: false
      });
    }, Errors.XTTemplateError, expectedError);
  });
});
describe("Rendering error", function () {
  it("should show an error when calling render twice", function () {
    var expectedError = {
      name: "InternalError",
      message: "You should not call .render twice on the same Docxtemplater instance",
      properties: {
        id: "render_twice"
      }
    };
    var doc = makeDocxV4("<w:t>{user}</w:t>").render();
    expectToThrow(function () {
      doc.render();
    }, Errors.XTInternalError, expectedError);
  });
  it("should show an error when using corrupt characters", function () {
    var expectedError = {
      name: "RenderingError",
      message: "There are some XML corrupt characters",
      properties: {
        id: "invalid_xml_characters",
        value: "\x1C",
        xtag: "user",
        offset: 1,
        file: "word/document.xml"
      }
    };
    expectToThrow(function () {
      makeDocxV4("<w:t> {user}</w:t>", {
        parser: expressionParser,
        errorLogging: false
      }).render({
        user: String.fromCharCode(28)
      });
    }, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
});
describe("Async errors", function () {
  it("should show error when having async promise", function () {
    var expectedError = {
      name: "ScopeParserError",
      message: "Scope parser execution failed",
      properties: {
        file: "word/document.xml",
        id: "scopeparser_execution_failed",
        xtag: "user",
        scope: {
          user: {}
        },
        rootError: {
          message: "Foobar"
        }
      }
    };
    var doc = makeDocxV4("<w:t>{user}</w:t>", {
      errorLogging: false
    });
    function create() {
      return doc.renderAsync({
        user: rejectSoon(new Error("Foobar"))
      });
    }
    return expectToThrowAsync(create, Errors.XTTemplateError, wrapMultiError(expectedError));
  });
  it("should show error when having async reject within loop", function () {
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_execution_failed",
            scope: 1,
            xtag: "user",
            rootError: {
              message: "foo 1"
            }
          }
        }, {
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_execution_failed",
            scope: 2,
            xtag: "user",
            rootError: {
              message: "foo 2"
            }
          }
        }, {
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            file: "word/document.xml",
            id: "scopeparser_execution_failed",
            scope: 3,
            xtag: "user",
            rootError: {
              message: "foo 3"
            }
          }
        }],
        id: "multi_error"
      }
    };
    var count = 0;
    function errorParser(tag) {
      return {
        get: function get() {
          if (tag === "users") {
            return [1, 2, 3];
          }
          count++;
          throw new Error("foo ".concat(count));
        }
      };
    }
    var doc = makeDocxV4("<w:t>{#users}{user}{/}</w:t>", {
      parser: errorParser,
      errorLogging: false
    });
    return expectToThrowAsync(function () {
      return doc.renderAsync({});
    }, Errors.XTTemplateError, expectedError);
  });
  it("should fail when customparser fails to execute on multiple tags", /*#__PURE__*/_asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee() {
    var count, errorParser, doc, create, myError, sortedErrors, rootErrorMessages, _i4, err, _t;
    return _regenerator().w(function (_context) {
      while (1) switch (_context.p = _context.n) {
        case 0:
          create = function _create() {
            return doc.renderAsync().then(function () {
              return doc.render();
            });
          };
          errorParser = function _errorParser() {
            return {
              get: function get() {
                count++;
                throw new Error("foo ".concat(count));
              }
            };
          };
          count = 0;
          /*
           * The order of the errors is not the same as the order of the tags in
           * the template, because each promise could resolve at a different
           * time.
           */
          doc = makeDocxV4("<w:t>{#name|istrue}Name{/} {name|upper} {othername|upper}</w:t>", {
            parser: errorParser,
            errorLogging: false
          });
          _context.p = 1;
          _context.n = 2;
          return create();
        case 2:
          _context.n = 4;
          break;
        case 3:
          _context.p = 3;
          _t = _context.v;
          myError = _t;
        case 4:
          expect(myError.message).to.equal("Multi error");
          sortedErrors = myError.properties.errors.sort(function (x, y) {
            if (x.properties.offset > y.properties.offset) {
              return 1;
            }
            return -1;
          });
          rootErrorMessages = [];
          for (_i4 = 0; _i4 < sortedErrors.length; _i4++) {
            err = sortedErrors[_i4];
            rootErrorMessages.push(err.properties.rootError.message);
          }
          expect(rootErrorMessages).to.deep.equal(["foo 1", "foo 2", "foo 3"]);
        case 5:
          return _context.a(2);
      }
    }, _callee, null, [[1, 3]]);
  })));
  it("should fail when customparser fails to execute on multiple raw tags", function () {
    var count = 0;
    function errorParser() {
      return {
        get: function get() {
          count++;
          throw new Error("foo ".concat(count));
        }
      };
    }
    var expectedError = {
      name: "TemplateError",
      message: "Multi error",
      properties: {
        errors: [{
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            id: "scopeparser_execution_failed",
            file: "word/document.xml",
            scope: {
              abc: true
            },
            xtag: "raw|isfalse",
            rootError: {
              message: "foo 1"
            },
            offset: 0
          }
        }, {
          name: "ScopeParserError",
          message: "Scope parser execution failed",
          properties: {
            id: "scopeparser_execution_failed",
            file: "word/document.xml",
            scope: {
              abc: true
            },
            xtag: "raw|istrue",
            rootError: {
              message: "foo 2"
            },
            offset: 14
          }
        }],
        id: "multi_error"
      }
    };
    var doc = makeDocxV4("\n\t\t\t\t<w:p><w:r><w:t>{@raw|isfalse}</w:t></w:r></w:p>\n\t\t\t\t<w:p><w:r><w:t>{@raw|istrue}</w:t></w:r></w:p>\n\t\t\t\t", {
      parser: errorParser,
      errorLogging: false
    });
    return expectToThrowAsync(function () {
      return doc.renderAsync({
        abc: true
      });
    }, Errors.XTTemplateError, expectedError);
  });
});
describe("Syntax option", function () {
  it("should be possible to allow unopened tag if syntax.allowUnopenedTag is true", function () {
    return this.renderV4({
      name: "bug-closing-placeholder-orphan.docx",
      expectedName: "expected-bug-closing-placeholder-orphan.docx",
      data: {
        first_name: "John",
        last_name: "Doe"
      },
      options: {
        delimiters: {
          start: "$(",
          end: ")"
        },
        syntax: {
          allowUnopenedTag: true
        }
      }
    });
  });
});
describe("Keep Postparse valid XML when having error in lexing", function () {
  /*
   * These types of tests have been added in version 3.68.2 and make sure that the postparsed is still complete after having a lexer error.
   *
   * In previous versions, the following template :
   *
   * ```docx
   * Hello {name
   *
   * Some other text
   * Foo bar
   * ```
   *
   * Would have its postparsed value set to :
   *
   * `[ { type: content, value: Hello}]`
   * __Note there is no content after the Hello in the postparsed value__
   *
   * This is clearly incorrect and removed the possibility for other modules to find other errors in the template (chart module for example in version 3.20.2 had this issue when having a template that has unclosed tags).
   */
  function getXmlPostparsedWithErrors(name, xml) {
    var pp = null;
    var ppModule = {
      name: "ppmodule",
      postparse: function postparse(postparsed) {
        pp = postparsed;
      }
    };
    var hasError = false;
    try {
      if (name) {
        createDocV4(name, {
          modules: [ppModule],
          errorLogging: false
        });
      } else {
        makeDocxV4(xml, {
          modules: [ppModule],
          errorLogging: false
        });
      }
    } catch (_unused) {
      hasError = true;
    }
    if (!hasError) {
      throw new Error("Expected to throw an error for this document '".concat(name, "'"));
    }
    var xmlPostparsed = "";
    for (var _i6 = 0, _pp2 = pp; _i6 < _pp2.length; _i6++) {
      var p = _pp2[_i6];
      xmlPostparsed += p.value + "\n";
    }
    return xmlPrettify(xmlPostparsed);
  }
  it("should work when having one unclosed tag", function () {
    var xmlPostparsed = getXmlPostparsedWithErrors("one-unclosed.docx");
    expect(xmlPrettify(xmlPostparsed)).to.matchSnapshot();
  });
  it("should work when having multiple unclosed tags", function () {
    var xmlPostparsed = getXmlPostparsedWithErrors("multiple-unclosed.docx");
    expect(xmlPrettify(xmlPostparsed)).to.matchSnapshot();
  });
  it("should work when having one unopened tag", function () {
    var xmlPostparsed = getXmlPostparsedWithErrors("one-unopened.docx");
    expect(xmlPrettify(xmlPostparsed)).to.matchSnapshot();
  });
  it("should work when having duplicate tags", function () {
    var xmlPostparsed = getXmlPostparsedWithErrors(false, "<w:p><w:r><w:t>{{name}}</w:t></w:r></w:p>");
    expect(xmlPrettify(xmlPostparsed)).to.matchSnapshot();
  });
  it("should work when having raw tags outside paragraph", function () {
    var xmlPostparsed = getXmlPostparsedWithErrors(false, "<w:t>{@myrawtag}</w:t>");
    expect(xmlPrettify(xmlPostparsed)).to.matchSnapshot();
  });
});