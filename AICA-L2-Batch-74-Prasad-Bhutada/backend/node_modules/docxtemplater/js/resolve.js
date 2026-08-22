"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var _require = require("./doc-utils.js"),
  pushArray = _require.pushArray;
var getResolvedId = require("./get-resolved-id.js");
function moduleResolve(part, options) {
  for (var _i2 = 0, _options$modules2 = options.modules; _i2 < _options$modules2.length; _i2++) {
    var _module = _options$modules2[_i2];
    var moduleResolved = _module.resolve(part, options);
    if (moduleResolved) {
      return moduleResolved;
    }
  }
  return false;
}
function resolvePart(part, resolved, errors, options) {
  var moduleResolved = moduleResolve(part, _objectSpread(_objectSpread({}, options), {}, {
    resolvedId: getResolvedId(part, options)
  }));
  if (moduleResolved) {
    return moduleResolved.then(function (value) {
      resolved.push({
        tag: part.value,
        lIndex: part.lIndex,
        value: value
      });
    })["catch"](function (e) {
      if (e instanceof Array) {
        pushArray(errors, e);
      } else {
        errors.push(e);
      }
    });
  }
  if (part.type === "placeholder") {
    return options.scopeManager.getValueAsync(part.value, {
      part: part
    }).then(function (value) {
      return value == null ? options.nullGetter(part) : value;
    }).then(function (value) {
      resolved.push({
        tag: part.value,
        lIndex: part.lIndex,
        value: value
      });
    })["catch"](function (e) {
      if (e instanceof Array) {
        pushArray(errors, e);
      } else {
        errors.push(e);
      }
    });
  }
}
function resolve(options) {
  var resolved = [];
  var errors = [];
  var baseNullGetter = options.baseNullGetter;
  var scopeManager = options.scopeManager;
  options.nullGetter = function (part, sm) {
    return baseNullGetter(part, sm || scopeManager);
  };
  options.resolved = resolved;
  var p = resolveSerial(options, errors, resolved);
  if (p) {
    return p.then(function () {
      return resolveParallel(options, errors, resolved);
    });
  }
  return resolveParallel(options, errors, resolved);
}
function resolveSerial(options, errors, resolved) {
  var p = null;
  var _loop = function _loop() {
    var part = _options$compiled2[_i4];
    if (["content", "tag"].indexOf(part.type) !== -1) {
      return 1; // continue
    }
    if (part.resolveFirst) {
      p !== null && p !== void 0 ? p : p = Promise.resolve(null);
      p = p.then(function () {
        return resolvePart(part, resolved, errors, options);
      });
    }
  };
  for (var _i4 = 0, _options$compiled2 = options.compiled; _i4 < _options$compiled2.length; _i4++) {
    if (_loop()) continue;
  }
  return p;
}
function resolveParallel(options, errors, resolved) {
  var promises = [];
  for (var _i6 = 0, _options$compiled4 = options.compiled; _i6 < _options$compiled4.length; _i6++) {
    var part = _options$compiled4[_i6];
    if (["content", "tag"].indexOf(part.type) !== -1) {
      continue;
    }
    if (!part.resolveFirst) {
      promises.push(resolvePart(part, resolved, errors, options));
    }
  }
  return Promise.all(promises).then(function () {
    return {
      errors: errors,
      resolved: resolved
    };
  });
}
module.exports = resolve;