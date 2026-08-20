"use strict";

function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _classCallCheck(a, n) { if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function"); }
function _defineProperties(e, r) { for (var t = 0; t < r.length; t++) { var o = r[t]; o.enumerable = o.enumerable || !1, o.configurable = !0, "value" in o && (o.writable = !0), Object.defineProperty(e, _toPropertyKey(o.key), o); } }
function _createClass(e, r, t) { return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", { writable: !1 }), e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var MiniZod = /*#__PURE__*/function () {
  function MiniZod() {
    _classCallCheck(this, MiniZod);
  }
  return _createClass(MiniZod, null, [{
    key: "createSchema",
    value: function createSchema(validateFn) {
      var schema = {
        validate: validateFn,
        optional: function optional() {
          return MiniZod.createSchema(function (value) {
            return value === undefined ? {
              success: true,
              value: value
            } : validateFn(value);
          });
        },
        nullable: function nullable() {
          return MiniZod.createSchema(function (value) {
            return value == null ? {
              success: true,
              value: value
            } : validateFn(value);
          });
        }
      };
      return schema;
    }
  }, {
    key: "string",
    value: function string() {
      return MiniZod.createSchema(function (value) {
        if (typeof value !== "string") {
          return {
            success: false,
            error: "Expected string, received ".concat(_typeof(value))
          };
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "date",
    value: function date() {
      return MiniZod.createSchema(function (value) {
        if (!(value instanceof Date)) {
          return {
            success: false,
            error: "Expected date, received ".concat(_typeof(value))
          };
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "boolean",
    value: function _boolean() {
      return MiniZod.createSchema(function (value) {
        if (typeof value !== "boolean") {
          return {
            success: false,
            error: "Expected boolean, received ".concat(_typeof(value))
          };
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "number",
    value: function number() {
      return MiniZod.createSchema(function (value) {
        if (typeof value !== "number") {
          return {
            success: false,
            error: "Expected number, received ".concat(_typeof(value))
          };
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "function",
    value: function _function() {
      return MiniZod.createSchema(function (value) {
        if (typeof value !== "function") {
          return {
            success: false,
            error: "Expected function, received ".concat(_typeof(value))
          };
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "array",
    value: function array(itemSchema) {
      return MiniZod.createSchema(function (value) {
        if (!Array.isArray(value)) {
          return {
            success: false,
            error: "Expected array, received ".concat(_typeof(value))
          };
        }
        for (var i = 0; i < value.length; i++) {
          var result = itemSchema.validate(value[i]);
          if (!result.success) {
            return {
              success: false,
              error: "".concat(result.error, " at index ").concat(i)
            };
          }
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "any",
    value: function any() {
      return MiniZod.createSchema(function (value) {
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "isRegex",
    value: function isRegex() {
      return MiniZod.createSchema(function (value) {
        if (!(value instanceof RegExp)) {
          return {
            success: false,
            error: "Expected RegExp, received ".concat(_typeof(value))
          };
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }, {
    key: "union",
    value: function union(schemas) {
      return MiniZod.createSchema(function (value) {
        for (var _i2 = 0; _i2 < schemas.length; _i2++) {
          var s = schemas[_i2];
          var result = s.validate(value);
          if (result.success) {
            return result;
          }
        }
        return {
          success: false,
          error: "Value ".concat(value, " does not match any schema in union")
        };
      });
    }
  }, {
    key: "object",
    value: function object(shape) {
      var schema = MiniZod.createSchema(function (value) {
        if (value == null) {
          return {
            success: false,
            error: "Expected object, received ".concat(value)
          };
        }
        if (_typeof(value) !== "object") {
          return {
            success: false,
            error: "Expected object, received ".concat(_typeof(value))
          };
        }
        for (var _i4 = 0, _Object$entries2 = Object.entries(shape); _i4 < _Object$entries2.length; _i4++) {
          var _Object$entries2$_i = _slicedToArray(_Object$entries2[_i4], 2),
            key = _Object$entries2$_i[0],
            validator = _Object$entries2$_i[1];
          var result = validator.validate(value[key]);
          if (!result.success) {
            return {
              success: false,
              error: "".concat(result.error, " at ").concat(key)
            };
          }
        }
        return {
          success: true,
          value: value
        };
      });
      schema.strict = function () {
        return MiniZod.createSchema(function (value) {
          var baseResult = schema.validate(value);
          if (!baseResult.success) {
            return baseResult;
          }
          var extraKeys = Object.keys(value).filter(function (key) {
            return !(key in shape);
          });
          if (extraKeys.length > 0) {
            return {
              success: false,
              error: "Unexpected properties: ".concat(extraKeys.join(", "))
            };
          }
          return baseResult;
        });
      };
      return schema;
    }
  }, {
    key: "record",
    value: function record(valueSchema) {
      return MiniZod.createSchema(function (value) {
        if (value === null) {
          return {
            success: false,
            error: "Expected object, received null"
          };
        }
        if (_typeof(value) !== "object") {
          return {
            success: false,
            error: "Expected object, received ".concat(_typeof(value))
          };
        }
        for (var _i6 = 0, _Object$keys2 = Object.keys(value); _i6 < _Object$keys2.length; _i6++) {
          var key = _Object$keys2[_i6];
          if (typeof key !== "string") {
            return {
              success: false,
              error: "Expected string key, received ".concat(_typeof(key), " at ").concat(key)
            };
          }
          var result = valueSchema.validate(value[key]);
          if (!result.success) {
            return {
              success: false,
              error: "".concat(result.error, " at key ").concat(key)
            };
          }
        }
        return {
          success: true,
          value: value
        };
      });
    }
  }]);
}();
module.exports = MiniZod;