"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _classCallCheck(a, n) { if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function"); }
function _defineProperties(e, r) { for (var t = 0; t < r.length; t++) { var o = r[t]; o.enumerable = o.enumerable || !1, o.configurable = !0, "value" in o && (o.writable = !0), Object.defineProperty(e, _toPropertyKey(o.key), o); } }
function _createClass(e, r, t) { return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", { writable: !1 }), e; }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var _require = require("lodash"),
  merge = _require.merge,
  cloneDeep = _require.cloneDeep;
var _require2 = require("./doc-utils.js"),
  pushArray = _require2.pushArray;
var _require3 = require("./get-tags.js"),
  isPlaceholder = _require3.isPlaceholder,
  _getTags = _require3.getTags;
var slideNumRegex = /ppt\/slides\/slide([0-9]+).xml/;
function throwUnattached(method) {
  throw new Error("You can not call Inspectmodule@".concat(method, " if the module was not attached. Please make sure to attach the module to a Docxtemplater instance with new Docxtemplater(zip, { modules: [inspectModule, ...]})"));
}
function getSlideIndex(path) {
  return parseInt(path.replace(slideNumRegex, "$1"), 10) - 1;
}
function _getStructuredTags(postParsed) {
  return postParsed.filter(isPlaceholder).map(function (part) {
    if (!part.subparsed && !part.attrParsed) {
      return part;
    }
    /*
     * #regression-postparsed-after-inspect-modified
     *
     * Copy the part instead of modifying it.
     * This fixes bugs when calling render after getStructuredTags for templates that contain loops.
     *
     * Fixed since v3.67.6
     */
    part = _objectSpread({}, part);
    if (part.subparsed) {
      var _part;
      (_part = part).subparsed && (_part.subparsed = _getStructuredTags(part.subparsed));
    }
    if (part.attrParsed) {
      part.subparsed = [];
      if (part.attrParsed) {
        part.subparsed = [];
        for (var key in part.attrParsed) {
          part.subparsed = part.subparsed.concat(part.attrParsed[key]);
        }
        return part;
      }
    }
    return part;
  }, {});
}
var InspectModule = /*#__PURE__*/function () {
  function InspectModule() {
    _classCallCheck(this, InspectModule);
    this.name = "InspectModule";
    this.inspect = {};
    this.fullInspected = {};
    this.filePath = null;
  }
  return _createClass(InspectModule, [{
    key: "clone",
    value: function clone() {
      return new InspectModule();
    }
  }, {
    key: "set",
    value: function set(obj) {
      if (obj.data) {
        this.inspect.tags = obj.data;
      }
      if (obj.pptxCustomMap) {
        this.pptxCustomMap = obj.pptxCustomMap;
      }
      if (obj.pptxSectionMap) {
        this.pptxSectionMap = obj.pptxSectionMap;
      }
      if (obj.inspect) {
        if (obj.inspect.filePath) {
          this.filePath = obj.inspect.filePath;
          this.inspect = this.fullInspected[this.filePath] || {};
        }
        if (obj.inspect.content) {
          this.inspect.content = obj.inspect.content;
        } else if (obj.inspect.postparsed) {
          this.inspect.postparsed = obj.inspect.postparsed;
        } else if (obj.inspect.parsed) {
          this.inspect.parsed = cloneDeep(obj.inspect.parsed);
        } else if (obj.inspect.lexed) {
          this.inspect.lexed = cloneDeep(obj.inspect.lexed);
        } else if (obj.inspect.xmllexed) {
          this.inspect.xmllexed = cloneDeep(obj.inspect.xmllexed);
        }
        if (obj.inspect.resolved) {
          this.inspect.resolved = obj.inspect.resolved;
        }
        this.fullInspected[this.filePath] = this.inspect;
      }
    }
  }, {
    key: "getFileType",
    value: function getFileType() {
      return this.fileType;
    }
  }, {
    key: "optionsTransformer",
    value: function optionsTransformer(options, docxtemplater) {
      this.fileTypeConfig = docxtemplater.fileTypeConfig;
      this.zip = docxtemplater.zip;
      this.targets = docxtemplater.targets;
      this.fileType = docxtemplater.fileType;
      this.docxtemplater = docxtemplater;
      return options;
    }
  }, {
    key: "nullGetter",
    value: function nullGetter(part, scopeManager, xt) {
      var inspected = this.fullInspected[xt.filePath];
      inspected.nullValues || (inspected.nullValues = {
        summary: [],
        detail: []
      });
      inspected.nullValues.detail.push({
        part: part,
        scopeManager: scopeManager
      });
      inspected.nullValues.summary.push(scopeManager.scopePath.concat(part.value));
    }
  }, {
    key: "getInspected",
    value: function getInspected(file) {
      if (!this.attached) {
        throwUnattached("getInspected");
      }
      var inspected = this.fullInspected[file].postparsed;
      var si = getSlideIndex(file);
      if (si != null && !isNaN(si)) {
        if (this.pptxCustomMap && this.pptxCustomMap[si]) {
          var map = this.pptxCustomMap[si];
          if (map) {
            inspected = [_objectSpread(_objectSpread({}, map), {}, {
              type: "placeholder",
              module: "pro-xml-templating/slides-module-repeat",
              subparsed: inspected
            })];
          }
        }
        if (this.pptxSectionMap) {
          for (var _i2 = 0, _this$pptxSectionMap2 = this.pptxSectionMap; _i2 < _this$pptxSectionMap2.length; _i2++) {
            var section = _this$pptxSectionMap2[_i2];
            if (section.slideIndexes.indexOf(si) !== -1) {
              inspected = [_objectSpread(_objectSpread({}, section.part), {}, {
                module: "pro-xml-templating/slides-module-section",
                subparsed: inspected,
                slideIndexes: section.slideIndexes,
                subIds: section.subIds
              })];
            }
          }
        }
      }
      return inspected;
    }
  }, {
    key: "getTags",
    value: function getTags(file) {
      if (!this.attached) {
        throwUnattached("getTags");
      }
      file || (file = this.fileTypeConfig.textPath(this.docxtemplater));
      var inspected = this.getInspected(file);
      return _getTags(inspected);
    }
  }, {
    key: "getAllTags",
    value: function getAllTags() {
      if (!this.attached) {
        throwUnattached("getAllTags");
      }
      var result = {};
      for (var file in this.fullInspected) {
        merge(result, this.getTags(file));
      }
      return result;
    }
  }, {
    key: "getStructuredTags",
    value: function getStructuredTags(file) {
      if (!this.attached) {
        throwUnattached("getStructuredTags");
      }
      file || (file = this.fileTypeConfig.textPath(this.docxtemplater));
      return _getStructuredTags(this.getInspected(file));
    }
  }, {
    key: "getAllStructuredTags",
    value: function getAllStructuredTags() {
      if (!this.attached) {
        throwUnattached("getAllStructuredTags");
      }
      var result = [];
      for (var file in this.fullInspected) {
        pushArray(result, this.getStructuredTags(file));
      }
      return result;
    }
  }, {
    key: "getTemplatedFiles",
    value: function getTemplatedFiles() {
      if (!this.attached) {
        throwUnattached("getTemplatedFiles");
      }
      return this.docxtemplater.templatedFiles;
    }
  }]);
}();
module.exports = function () {
  return new InspectModule();
};