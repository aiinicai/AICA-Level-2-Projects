"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _classCallCheck(a, n) { if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function"); }
function _defineProperties(e, r) { for (var t = 0; t < r.length; t++) { var o = r[t]; o.enumerable = o.enumerable || !1, o.configurable = !0, "value" in o && (o.writable = !0), Object.defineProperty(e, _toPropertyKey(o.key), o); } }
function _createClass(e, r, t) { return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", { writable: !1 }), e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var Docxtemplater = require("../../docxtemplater.js");
var _require = require("../utils.js"),
  createDocV4 = _require.createDocV4,
  expect = _require.expect,
  getZip = _require.getZip,
  captureLogs = _require.captureLogs;
var inspectModule = require("../../inspect-module.js");
describe("Constructor v4", function () {
  it("should work when modules are attached", function () {
    var isModuleCalled = false;
    var module = {
      name: "TestModule",
      optionsTransformer: function optionsTransformer(options) {
        isModuleCalled = true;
        return options;
      }
    };
    createDocV4("tag-example.docx", {
      modules: [module]
    });
    expect(isModuleCalled).to.equal(true);
  });
  it("should throw an error when modules passed is not an array", function () {
    expect(function () {
      return new Docxtemplater(getZip("tag-example.docx"), {
        modules: {}
      });
    }).to["throw"]("The modules argument of docxtemplater's constructor must be an array");
  });
  it("should warn if trying to reuse same zip for two docxtemplater templates", function () {
    var zip = getZip("tag-example.docx");
    var doc = new Docxtemplater(zip);
    var capture = captureLogs();
    doc.render();
    /* eslint-disable-next-line no-unused-vars */
    var otherDoc = new Docxtemplater(zip);
    capture.stop();
    var logs = capture.logs();
    expect(logs).to.deep.equal(["Warning : This zip file appears to be the outcome of a previous docxtemplater generation. This typically indicates that docxtemplater was integrated by reusing the same zip file. It is recommended to create a new Pizzip instance for each docxtemplater generation."]);
  });
  it("should be possible to customize warnFn", function () {
    var zip = getZip("tag-example.docx");
    var doc = new Docxtemplater(zip);
    doc.render();
    var myErrors = [];
    /* eslint-disable-next-line no-unused-vars */
    var otherDoc = new Docxtemplater(zip, {
      warnFn: function warnFn(errors) {
        myErrors = errors;
      }
    });
    expect(myErrors.length).to.deep.equal(1);
    expect(myErrors[0]).to.be["instanceof"](Error);
  });
  it("should throw an error when an invalid zip is passed", function () {
    expect(function () {
      return new Docxtemplater("content");
    }).to["throw"]("The first argument of docxtemplater's constructor must be a valid zip file (jszip v2 or pizzip v3)");
    expect(function () {
      return new Docxtemplater({
        files: []
      });
    }).to["throw"]("The first argument of docxtemplater's constructor must be a valid zip file (jszip v2 or pizzip v3)");
    var zip = getZip("tag-example.docx");
    zip.files = null;
    expect(function () {
      return new Docxtemplater(zip);
    }).to["throw"]("The first argument of docxtemplater's constructor must be a valid zip file (jszip v2 or pizzip v3)");
    if (typeof Buffer !== "undefined") {
      expect(function () {
        return new Docxtemplater(Buffer.from("content"));
      }).to["throw"]("You passed a Buffer to the Docxtemplater constructor. The first argument of docxtemplater's constructor must be a valid zip file (jszip v2 or pizzip v3)");
    }
  });
  it("should work when the delimiters are passed", function () {
    var options = {
      delimiters: {
        start: "<",
        end: ">"
      }
    };
    var doc = createDocV4("delimiter-gt.docx", options);
    doc.render({
      user: "John"
    });
    expect(doc.getFullText()).to.be.equal("Hello John");
  });
  it("should work when both modules and delimiters are passed and modules should have access to options object", function () {
    var isModuleCalled = false,
      optionsPassedToModule;
    var options = {
      delimiters: {
        start: "%",
        end: "%"
      },
      modules: [{
        name: "MyModule",
        optionsTransformer: function optionsTransformer(options) {
          optionsPassedToModule = options;
          isModuleCalled = true;
          return options;
        }
      }]
    };
    var doc = createDocV4("delimiter-pct.docx", options);
    expect(isModuleCalled).to.be.equal(true);
    expect(optionsPassedToModule.delimiters.start).to.be.equal("%");
    expect(optionsPassedToModule.delimiters.end).to.be.equal("%");
    // Verify that default options are passed to the modules
    expect(optionsPassedToModule.linebreaks).to.be.equal(false);
    doc.render({
      user: "John",
      company: "Acme"
    });
    expect(doc.getFullText()).to.be.equal("Hello John from Acme");
  });
  it("should throw error when using a non-instanciated class as a module", function () {
    var MyTestModule = /*#__PURE__*/function () {
      function MyTestModule() {
        _classCallCheck(this, MyTestModule);
      }
      return _createClass(MyTestModule, [{
        key: "render",
        value: function render(part) {
          return {
            value: part.value
          };
        }
      }]);
    }();
    var options = {
      delimiters: {
        start: "%",
        end: "%"
      },
      modules: [MyTestModule]
    };
    expect(function () {
      return createDocV4("delimiter-pct.docx", options);
    }).to["throw"]("Cannot attach a class/function as a module. Most probably you forgot to instantiate the module by using `new` on the module.");
  });
  it("should throw if using v4 constructor and setOptions", function () {
    var doc = createDocV4("tag-example.docx");
    expect(function () {
      return doc.setOptions({
        linebreaks: true
      });
    }).to["throw"]("setOptions() should not be called manually when using the v4 constructor");
  });
  it("should throw if using v4 constructor and attachModule", function () {
    var doc = createDocV4("tag-example.docx");
    expect(function () {
      return doc.attachModule({
        render: function render() {}
      });
    }).to["throw"]("attachModule() should not be called manually when using the v4 constructor");
  });
  it("should throw if using v4 constructor and loadZip", function () {
    var doc = createDocV4("tag-example.docx");
    expect(function () {
      return doc.loadZip();
    }).to["throw"]("loadZip() should not be called manually when using the v4 constructor");
  });
  it("should render correctly", function () {
    var doc = new Docxtemplater(getZip("tag-example.docx"));
    doc.render({
      first_name: "John",
      last_name: "Doe"
    });
    expect(doc.getFullText()).to.be.equal("Doe John");
  });
  it("should work when modules are attached with valid filetypes", function () {
    var isModuleCalled = false;
    var module = {
      name: "FooModule",
      optionsTransformer: function optionsTransformer(options) {
        isModuleCalled = true;
        return options;
      },
      supportedFileTypes: ["pptx", "docx"]
    };
    createDocV4("tag-example.docx", {
      modules: [module]
    });
    expect(isModuleCalled).to.equal(true);
  });
  it("should throw an error when supportedFieldType property in passed module is not an Array", function () {
    var zip = getZip("tag-example.docx");
    var module = {
      optionsTransformer: function optionsTransformer(options) {
        return options;
      },
      supportedFileTypes: "pptx"
    };
    expect(function () {
      return new Docxtemplater(zip, {
        modules: [module]
      });
    }).to["throw"]("The supportedFileTypes field of the module must be an array");
  });
  it("should fail with readable error when using new Docxtemplater(null)", function () {
    expect(function () {
      return new Docxtemplater(null, {});
    }).to["throw"]("The first argument of docxtemplater's constructor must be a valid zip file (jszip v2 or pizzip v3)");
  });
  it("should fail with readable error when using new Docxtemplater(null, {modules: [inspectModule()]})", function () {
    expect(function () {
      return new Docxtemplater(null, {
        modules: [inspectModule()]
      });
    }).to["throw"]("The first argument of docxtemplater's constructor must be a valid zip file (jszip v2 or pizzip v3)");
  });
});