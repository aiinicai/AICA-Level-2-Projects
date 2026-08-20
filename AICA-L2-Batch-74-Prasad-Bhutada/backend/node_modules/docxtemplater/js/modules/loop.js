"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
function _classCallCheck(a, n) { if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function"); }
function _defineProperties(e, r) { for (var t = 0; t < r.length; t++) { var o = r[t]; o.enumerable = o.enumerable || !1, o.configurable = !0, "value" in o && (o.writable = !0), Object.defineProperty(e, _toPropertyKey(o.key), o); } }
function _createClass(e, r, t) { return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", { writable: !1 }), e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var _require = require("../doc-utils.js"),
  chunkBy = _require.chunkBy,
  last = _require.last,
  isParagraphStart = _require.isParagraphStart,
  isModule = _require.isModule,
  pushArray = _require.pushArray,
  isParagraphEnd = _require.isParagraphEnd,
  isContent = _require.isContent,
  startsWith = _require.startsWith,
  isTagEnd = _require.isTagEnd,
  isTagStart = _require.isTagStart,
  getSingleAttribute = _require.getSingleAttribute,
  setSingleAttribute = _require.setSingleAttribute;
var filetypes = require("../filetypes.js");
var wrapper = require("../module-wrapper.js");
var _require2 = require("../doc-utils.js"),
  isWhiteSpace = _require2.isWhiteSpace;
var moduleName = "loop";
function hasContent(parts) {
  for (var _i2 = 0; _i2 < parts.length; _i2++) {
    var part = parts[_i2];
    if (isContent(part)) {
      return true;
    }
  }
  return false;
}
function getFirstMeaningFulPart(parsed) {
  for (var _i4 = 0; _i4 < parsed.length; _i4++) {
    var part = parsed[_i4];
    if (part.type !== "content") {
      return part;
    }
  }
  return null;
}
function isInsideParagraphLoop(part) {
  var firstMeaningfulPart = getFirstMeaningFulPart(part.subparsed);
  return firstMeaningfulPart != null && firstMeaningfulPart.tag !== "w:t";
}
function getPageBreakIfApplies(part) {
  return part.hasPageBreak && isInsideParagraphLoop(part) ? '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' : "";
}
function isEnclosedByParagraphs(parsed) {
  return parsed.length && isParagraphStart(parsed[0]) && isParagraphEnd(last(parsed));
}
function getOffset(chunk) {
  return hasContent(chunk) ? 0 : chunk.length;
}
function addPageBreakAtEnd(subRendered) {
  var j = subRendered.parts.length - 1;
  if (subRendered.parts[j] === "</w:p>") {
    subRendered.parts.splice(j, 0, '<w:r><w:br w:type="page"/></w:r>');
  } else {
    subRendered.parts.push('<w:p><w:r><w:br w:type="page"/></w:r></w:p>');
  }
}
function addPageBreakAtBeginning(subRendered) {
  subRendered.parts.unshift('<w:p><w:r><w:br w:type="page"/></w:r></w:p>');
}
function isContinuous(parts) {
  for (var _i6 = 0; _i6 < parts.length; _i6++) {
    var part = parts[_i6];
    if (isTagStart("w:type", part) && part.value.indexOf("continuous") !== -1) {
      return true;
    }
  }
  return false;
}
function isNextPage(parts) {
  for (var _i8 = 0; _i8 < parts.length; _i8++) {
    var part = parts[_i8];
    if (isTagStart("w:type", part) && part.value.indexOf('w:val="nextPage"') !== -1) {
      return true;
    }
  }
  return false;
}
function addSectionBefore(parts, sect) {
  var result = "";
  for (var _i0 = 0; _i0 < sect.length; _i0++) {
    var value = sect[_i0].value;
    result += value;
  }
  parts.unshift("<w:p><w:pPr>".concat(result, "</w:pPr></w:p>"));
}
function addContinuousType(parts) {
  var stop = false;
  var inSectPr = false;
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (!stop && startsWith(part, "<w:sectPr")) {
      inSectPr = true;
    }
    if (inSectPr) {
      if (startsWith(part, "<w:type")) {
        stop = true;
      }
      if (!stop && startsWith(part, "</w:sectPr")) {
        parts.splice(i, 0, '<w:type w:val="continuous"/>');
        i++; // Skip re-processing the now-shifted closing tag to avoid infinite insertion
      }
    }
  }
  return parts;
}
function dropHeaderFooterRefs(parts) {
  var writeIndex = 0;
  for (var readIndex = 0; readIndex < parts.length; readIndex++) {
    if (!startsWith(parts[readIndex], "<w:headerReference") && !startsWith(parts[readIndex], "<w:footerReference")) {
      parts[writeIndex] = parts[readIndex];
      writeIndex++;
    }
  }
  parts.length = writeIndex;
  return parts;
}
function hasPageBreak(chunk) {
  for (var _i10 = 0; _i10 < chunk.length; _i10++) {
    var part = chunk[_i10];
    if (part.tag === "w:br" && part.value.indexOf('w:type="page"') !== -1) {
      return true;
    }
  }
  return false;
}
function hasImage(chunk) {
  for (var _i12 = 0; _i12 < chunk.length; _i12++) {
    var el = chunk[_i12];
    if (el.tag === "w:drawing") {
      return true;
    }
  }
  return false;
}
function getSectPr(chunks) {
  var sectPrs = [];
  var currentSectPr = null;
  for (var _i14 = 0; _i14 < chunks.length; _i14++) {
    var part = chunks[_i14];
    if (isTagStart("w:sectPr", part)) {
      currentSectPr = [];
      sectPrs.push(currentSectPr);
    }
    if (currentSectPr !== null) {
      currentSectPr.push(part);
    }
    if (isTagEnd("w:sectPr", part)) {
      currentSectPr = null;
    }
  }
  return sectPrs;
}
function getSectPrHeaderFooterChangeCount(chunks) {
  var collectSectPr = false;
  var sectPrCount = 0;
  for (var _i16 = 0; _i16 < chunks.length; _i16++) {
    var part = chunks[_i16];
    if (isTagStart("w:sectPr", part)) {
      collectSectPr = true;
    }
    if (collectSectPr) {
      if (part.tag === "w:headerReference" || part.tag === "w:footerReference") {
        sectPrCount++;
        collectSectPr = false;
      }
    }
    if (isTagEnd("w:sectPr", part)) {
      collectSectPr = false;
    }
  }
  return sectPrCount;
}
function getLastSectPr(parsed) {
  var sectPr = [];
  var inSectPr = false;
  for (var i = parsed.length - 1; i >= 0; i--) {
    var part = parsed[i];

    /*
     * Since we try to get the last sectPr, we traverse the parsed array
     * from the end to beginning, this is why inSectPr becomes true when we
     * we see a </w:sectPr> closing tag
     */
    if (isTagEnd("w:sectPr", part)) {
      inSectPr = true;
    }
    if (isTagStart("w:sectPr", part)) {
      sectPr.unshift(part.value);
      inSectPr = false;
    }
    if (inSectPr) {
      sectPr.unshift(part.value);
    }
    if (isParagraphStart(part)) {
      if (sectPr.length > 0) {
        return sectPr.join("");
      }
      break;
    }
  }
  return "";
}
var LoopModule = /*#__PURE__*/function () {
  function LoopModule() {
    _classCallCheck(this, LoopModule);
    this.name = "LoopModule";
    this.inXfrm = false;
    this.totalSectPr = 0;
    this.prefix = {
      start: "#",
      end: "/",
      dash: /^-([^\s]+)\s(.+)/,
      inverted: "^"
    };
  }
  return _createClass(LoopModule, [{
    key: "optionsTransformer",
    value: function optionsTransformer(opts, docxtemplater) {
      this.docxtemplater = docxtemplater;
      return opts;
    }
  }, {
    key: "preparse",
    value: function preparse(parsed, _ref) {
      var contentType = _ref.contentType;
      if (filetypes.main.indexOf(contentType) !== -1) {
        this.sects = getSectPr(parsed);
      }
    }
  }, {
    key: "matchers",
    value: function matchers() {
      var module = moduleName;
      return [[this.prefix.start, module, {
        expandTo: "auto",
        location: "start",
        inverted: false
      }], [this.prefix.inverted, module, {
        expandTo: "auto",
        location: "start",
        inverted: true
      }], [this.prefix.end, module, {
        location: "end"
      }], [this.prefix.dash, module, function (_ref2) {
        var _ref3 = _slicedToArray(_ref2, 3),
          expandTo = _ref3[1],
          value = _ref3[2];
        return {
          location: "start",
          inverted: false,
          expandTo: expandTo,
          value: value
        };
      }]];
    }
  }, {
    key: "getTraits",
    value: function getTraits(traitName, parsed) {
      // Stryker disable all : because getTraits should disappear in v4
      if (traitName !== "expandPair") {
        return;
      }
      // Stryker restore all

      var tags = [];
      for (var offset = 0, len = parsed.length; offset < len; offset++) {
        var part = parsed[offset];
        if (isModule(part, moduleName) && part.subparsed == null) {
          tags.push({
            part: part,
            offset: offset
          });
        }
      }
      return tags;
    }

    /* eslint-disable-next-line complexity */
  }, {
    key: "postparse",
    value: function postparse(parsed, _ref4) {
      var basePart = _ref4.basePart;
      if (basePart && this.docxtemplater.fileType === "docx" && parsed.length > 0) {
        basePart.sectPrCount = getSectPrHeaderFooterChangeCount(parsed);
        this.totalSectPr += basePart.sectPrCount;
        var sects = this.sects;
        for (var index = 0, len = sects.length; index < len; index++) {
          var sect = sects[index];
          if (basePart.lIndex < sect[0].lIndex) {
            if (index + 1 < sects.length && isContinuous(sects[index + 1])) {
              basePart.addContinuousType = true;
            }
            break;
          }
          if (parsed[0].lIndex < sect[0].lIndex && sect[0].lIndex < basePart.lIndex) {
            if (isNextPage(sects[index])) {
              basePart.addNextPage = {
                index: index
              };
            }
            break;
          }
        }
        basePart.lastParagrapSectPr = getLastSectPr(parsed);
      }
      if (!basePart || basePart.expandTo !== "auto" || basePart.module !== moduleName || !isEnclosedByParagraphs(parsed)) {
        return parsed;
      }
      basePart.paragraphLoop = true;
      var level = 0;
      var chunks = chunkBy(parsed, function (p) {
        if (isParagraphStart(p)) {
          level++;
          if (level === 1) {
            return "start";
          }
        }
        if (isParagraphEnd(p)) {
          level--;
          if (level === 0) {
            return "end";
          }
        }
        return null;
      });
      var firstChunk = chunks[0];
      var lastChunk = last(chunks);
      var firstOffset = getOffset(firstChunk);
      var lastOffset = getOffset(lastChunk);
      if (firstOffset > 0 && chunks[1][0].type === "content" && isWhiteSpace(chunks[1][0].value)) {
        firstOffset += 1;
      }
      if (lastOffset > 0 && last(chunks[chunks.length - 2]).type === "content" && isWhiteSpace(last(chunks[chunks.length - 2]).value)) {
        lastOffset += 1;
      }
      basePart.hasPageBreakBeginning = hasPageBreak(firstChunk);
      basePart.hasPageBreak = hasPageBreak(lastChunk);
      if (hasImage(firstChunk)) {
        firstOffset = 0;
      }
      if (hasImage(lastChunk)) {
        lastOffset = 0;
      }
      return parsed.slice(firstOffset, parsed.length - lastOffset);
    }
  }, {
    key: "resolve",
    value: function resolve(part, options) {
      var self = this;
      if (!isModule(part, moduleName)) {
        return null;
      }
      var sm = options.scopeManager;
      var promisedValue = sm.getValueAsync(part.value, {
        part: part
      });
      var promises = [];
      var lastPromise;
      if (self.resolveSerially) {
        lastPromise = Promise.resolve(null);
      }
      function loopOver(scope, i, length) {
        var scopeManager = sm.createSubScopeManager(scope, part.value, i, part, length);
        if (self.resolveSerially) {
          lastPromise = lastPromise.then(function () {
            return options.resolve(_objectSpread(_objectSpread({}, options), {}, {
              compiled: part.subparsed,
              tags: {},
              scopeManager: scopeManager
            }));
          });
          promises.push(lastPromise);
        } else {
          promises.push(options.resolve(_objectSpread(_objectSpread({}, options), {}, {
            compiled: part.subparsed,
            tags: {},
            scopeManager: scopeManager
          })));
        }
      }
      var errorList = [];
      return promisedValue.then(function (values) {
        values !== null && values !== void 0 ? values : values = options.nullGetter(part);
        if (values instanceof Promise) {
          return values.then(function (values) {
            if (values instanceof Array) {
              return Promise.all(values);
            }
            return values;
          });
        }
        if (values instanceof Array) {
          return Promise.all(values);
        }
        return values;
      }).then(function (values) {
        sm.loopOverValue(values, loopOver, part.inverted);
        return Promise.all(promises).then(function (r) {
          var result = [];
          for (var _i18 = 0; _i18 < r.length; _i18++) {
            var _r$_i = r[_i18],
              resolved = _r$_i.resolved,
              errors = _r$_i.errors;
            pushArray(errorList, errors);
            result.push(resolved);
          }
          return result;
        }).then(function (value) {
          if (errorList.length > 0) {
            throw errorList;
          }
          return value;
        });
      });
    }
  }, {
    key: "render",
    value: function render(part, options) {
      var self = this;
      if (part.tag === "p:xfrm") {
        self.inXfrm = part.position === "start";
      }
      if (part.tag === "a:ext" && self.inXfrm) {
        self.lastExt = part;
        return part;
      }
      if (!isModule(part, moduleName)) {
        return null;
      }
      var totalValue = [];
      var errors = [];
      var heightOffset = 0;
      var firstTag = part.subparsed[0];
      var tagHeight = 0;
      if ((firstTag === null || firstTag === void 0 ? void 0 : firstTag.tag) === "a:tr") {
        tagHeight = +getSingleAttribute(firstTag.value, "h");
      }
      heightOffset -= tagHeight;
      var a16RowIdOffset = 0;
      var insideParagraphLoop = isInsideParagraphLoop(part);
      function loopOver(scope, i, length) {
        heightOffset += tagHeight;
        var scopeManager = options.scopeManager.createSubScopeManager(scope, part.value, i, part, length);
        for (var _i20 = 0, _part$subparsed2 = part.subparsed; _i20 < _part$subparsed2.length; _i20++) {
          var pp = _part$subparsed2[_i20];
          if (isTagStart("a16:rowId", pp)) {
            var val = +getSingleAttribute(pp.value, "val") + a16RowIdOffset;
            a16RowIdOffset = 1;
            pp.value = setSingleAttribute(pp.value, "val", val);
          }
        }
        var subRendered = options.render(_objectSpread(_objectSpread({}, options), {}, {
          compiled: part.subparsed,
          tags: {},
          scopeManager: scopeManager
        }));
        if (part.hasPageBreak && i === length - 1 && insideParagraphLoop) {
          addPageBreakAtEnd(subRendered);
        }
        var isNotFirst = scopeManager.scopePathItem.some(function (i) {
          return i !== 0;
        });
        if (isNotFirst) {
          if (part.sectPrCount === 1) {
            subRendered.parts = dropHeaderFooterRefs(subRendered.parts);
          }
          if (part.addContinuousType) {
            subRendered.parts = addContinuousType(subRendered.parts);
          }
        } else if (part.addNextPage) {
          addSectionBefore(subRendered.parts, self.sects[part.addNextPage.index]);
        }
        if (part.addNextPage) {
          addPageBreakAtEnd(subRendered);
        }
        if (part.hasPageBreakBeginning && insideParagraphLoop) {
          addPageBreakAtBeginning(subRendered);
        }
        for (var _i22 = 0, _subRendered$parts2 = subRendered.parts; _i22 < _subRendered$parts2.length; _i22++) {
          var _val = _subRendered$parts2[_i22];
          totalValue.push(_val);
        }
        pushArray(errors, subRendered.errors);
      }
      var value = options.scopeManager.getValue(part.value, {
        part: part
      });
      value !== null && value !== void 0 ? value : value = options.nullGetter(part);
      var result = options.scopeManager.loopOverValue(value, loopOver, part.inverted);
      // if the loop is showing empty content
      if (result === false) {
        if (part.lastParagrapSectPr) {
          if (part.paragraphLoop) {
            return {
              value: "<w:p><w:pPr>".concat(part.lastParagrapSectPr, "</w:pPr></w:p>")
            };
          }
          return {
            value: "</w:t></w:r></w:p><w:p><w:pPr>".concat(part.lastParagrapSectPr, "</w:pPr><w:r><w:t>")
          };
        }
        return {
          value: getPageBreakIfApplies(part) || "",
          errors: errors
        };
      }
      if (heightOffset !== 0) {
        var cy = +getSingleAttribute(self.lastExt.value, "cy");
        /*
         * We do edit the value of a previous result here
         * #edit-value-backwards
         */
        self.lastExt.value = setSingleAttribute(self.lastExt.value, "cy", cy + heightOffset);
      }
      return {
        value: options.joinUncorrupt(totalValue, _objectSpread(_objectSpread({}, options), {}, {
          basePart: part
        })),
        errors: errors
      };
    }
  }]);
}();
module.exports = function () {
  return wrapper(new LoopModule());
};