"use strict";

var MiniZod = require("../../minizod.js");
var _require = require("../utils.js"),
  expect = _require.expect;
describe("MiniZod", function () {
  describe("string", function () {
    var stringSchema = MiniZod.string();
    it("should validate string correctly", function () {
      expect(stringSchema.validate("hello")).to.deep.equal({
        success: true,
        value: "hello"
      });
      expect(stringSchema.validate("")).to.deep.equal({
        success: true,
        value: ""
      });
    });
    it("should fail for non-string values", function () {
      expect(stringSchema.validate(123)).to.deep.equal({
        success: false,
        error: "Expected string, received number"
      });
      expect(stringSchema.validate(null)).to.deep.equal({
        success: false,
        error: "Expected string, received object"
      });
    });
  });
  describe("date", function () {
    var dateSchema = MiniZod.date();
    it("should validate Date objects correctly", function () {
      var date = new Date();
      expect(dateSchema.validate(date)).to.deep.equal({
        success: true,
        value: date
      });
    });
    it("should fail for non-Date values", function () {
      expect(dateSchema.validate("2023-01-01")).to.deep.equal({
        success: false,
        error: "Expected date, received string"
      });
      expect(dateSchema.validate(null)).to.deep.equal({
        success: false,
        error: "Expected date, received object"
      });
    });
  });
  describe("boolean", function () {
    var booleanSchema = MiniZod["boolean"]();
    it("should validate boolean values correctly", function () {
      expect(booleanSchema.validate(true)).to.deep.equal({
        success: true,
        value: true
      });
      expect(booleanSchema.validate(false)).to.deep.equal({
        success: true,
        value: false
      });
    });
    it("should fail for non-boolean values", function () {
      expect(booleanSchema.validate("true")).to.deep.equal({
        success: false,
        error: "Expected boolean, received string"
      });
      expect(booleanSchema.validate(1)).to.deep.equal({
        success: false,
        error: "Expected boolean, received number"
      });
    });
  });
  describe("number", function () {
    var numberSchema = MiniZod.number();
    it("should validate number values correctly", function () {
      expect(numberSchema.validate(42)).to.deep.equal({
        success: true,
        value: 42
      });
      expect(numberSchema.validate(0)).to.deep.equal({
        success: true,
        value: 0
      });
      expect(numberSchema.validate(-10.5)).to.deep.equal({
        success: true,
        value: -10.5
      });
    });
    it("should fail for non-number values", function () {
      expect(numberSchema.validate("42")).to.deep.equal({
        success: false,
        error: "Expected number, received string"
      });
      expect(numberSchema.validate(null)).to.deep.equal({
        success: false,
        error: "Expected number, received object"
      });
    });
  });
  describe("function", function () {
    var functionSchema = MiniZod["function"]();
    it("should validate function values correctly", function () {
      function fn() {}
      expect(functionSchema.validate(fn)).to.deep.equal({
        success: true,
        value: fn
      });
    });
    it("should fail for non-function values", function () {
      expect(functionSchema.validate("function")).to.deep.equal({
        success: false,
        error: "Expected function, received string"
      });
      expect(functionSchema.validate({})).to.deep.equal({
        success: false,
        error: "Expected function, received object"
      });
    });
  });
  describe("array", function () {
    var arraySchema = MiniZod.array(MiniZod.string());
    it("should validate array of valid items correctly", function () {
      expect(arraySchema.validate(["hello", "world"])).to.deep.equal({
        success: true,
        value: ["hello", "world"]
      });
      expect(arraySchema.validate([])).to.deep.equal({
        success: true,
        value: []
      });
    });
    it("should fail for non-array values", function () {
      expect(arraySchema.validate("not an array")).to.deep.equal({
        success: false,
        error: "Expected array, received string"
      });
    });
    it("should fail for array with invalid items", function () {
      expect(arraySchema.validate(["hello", 123])).to.deep.equal({
        success: false,
        error: "Expected string, received number at index 1"
      });
    });
  });
  describe("any", function () {
    var anySchema = MiniZod.any();
    it("should validate any value", function () {
      expect(anySchema.validate("string")).to.deep.equal({
        success: true,
        value: "string"
      });
      expect(anySchema.validate(123)).to.deep.equal({
        success: true,
        value: 123
      });
      expect(anySchema.validate(null)).to.deep.equal({
        success: true,
        value: null
      });
      expect(anySchema.validate(undefined)).to.deep.equal({
        success: true,
        value: undefined
      });
    });
  });
  describe("isRegex", function () {
    var regexSchema = MiniZod.isRegex();
    it("should validate RegExp objects correctly", function () {
      var regex = /it/;
      expect(regexSchema.validate(regex)).to.deep.equal({
        success: true,
        value: regex
      });
      var r = new RegExp("it");
      expect(regexSchema.validate(new RegExp("it"))).to.deep.equal({
        success: true,
        value: r
      });
    });
    it("should fail for non-RegExp values", function () {
      expect(regexSchema.validate("/it/")).to.deep.equal({
        success: false,
        error: "Expected RegExp, received string"
      });
      expect(regexSchema.validate({})).to.deep.equal({
        success: false,
        error: "Expected RegExp, received object"
      });
    });
  });
  describe("union", function () {
    var unionSchema = MiniZod.union([MiniZod.string(), MiniZod.number()]);
    it("should validate values matching any schema in union", function () {
      expect(unionSchema.validate("hello")).to.deep.equal({
        success: true,
        value: "hello"
      });
      expect(unionSchema.validate(42)).to.deep.equal({
        success: true,
        value: 42
      });
    });
    it("should fail for values not matching any schema", function () {
      expect(unionSchema.validate(true)).to.deep.equal({
        success: false,
        error: "Value true does not match any schema in union"
      });
    });
  });
  describe("object", function () {
    var objectSchema = MiniZod.object({
      name: MiniZod.string(),
      age: MiniZod.number()
    });
    it("should validate object with correct shape", function () {
      expect(objectSchema.validate({
        name: "John",
        age: 30
      })).to.deep.equal({
        success: true,
        value: {
          name: "John",
          age: 30
        }
      });
    });
    it("should fail for invalid object shape", function () {
      expect(objectSchema.validate({
        name: "John",
        age: "30"
      })).to.deep.equal({
        success: false,
        error: "Expected number, received string at age"
      });
      expect(objectSchema.validate({
        name: "John"
      })).to.deep.equal({
        success: false,
        error: "Expected number, received undefined at age"
      });
    });
    it("should fail when passing false / null / undefined", function () {
      expect(objectSchema.validate(false)).to.deep.equal({
        success: false,
        error: "Expected object, received boolean"
      });
      expect(objectSchema.validate(null)).to.deep.equal({
        success: false,
        error: "Expected object, received null"
      });
      expect(objectSchema.validate(undefined)).to.deep.equal({
        success: false,
        error: "Expected object, received undefined"
      });
    });
    it("strict mode should fail on extra properties", function () {
      var strictSchema = objectSchema.strict();
      expect(strictSchema.validate({
        name: "John",
        age: 30,
        extra: "value"
      })).to.deep.equal({
        success: false,
        error: "Unexpected properties: extra"
      });
    });
    it("strict mode should fail on multiple extra properties", function () {
      var strictSchema = objectSchema.strict();
      expect(strictSchema.validate({
        name: "John",
        age: 30,
        extra: "value",
        extra2: true
      })).to.deep.equal({
        success: false,
        error: "Unexpected properties: extra, extra2"
      });
    });
    it("strict mode should fail if wrong", function () {
      var strictSchema = objectSchema.strict();
      expect(strictSchema.validate({
        name: "John"
      })).to.deep.equal({
        success: false,
        error: "Expected number, received undefined at age"
      });
    });
    it("strict mode should work with normal", function () {
      var strictSchema = objectSchema.strict();
      expect(strictSchema.validate({
        name: "John",
        age: 30
      })).to.deep.equal({
        success: true,
        value: {
          name: "John",
          age: 30
        }
      });
    });
    it("should allow extra properties in non-strict mode", function () {
      expect(objectSchema.validate({
        name: "John",
        age: 30,
        extra: "value"
      })).to.deep.equal({
        success: true,
        value: {
          name: "John",
          age: 30,
          extra: "value"
        }
      });
    });
  });
  describe("record", function () {
    var recordSchema = MiniZod.record(MiniZod.number());
    it("should validate record with valid values", function () {
      expect(recordSchema.validate({
        a: 1,
        b: 2
      })).to.deep.equal({
        success: true,
        value: {
          a: 1,
          b: 2
        }
      });
    });
    it("should fail for non-object values", function () {
      expect(recordSchema.validate("not an object")).to.deep.equal({
        success: false,
        error: "Expected object, received string"
      });
      expect(recordSchema.validate(null)).to.deep.equal({
        success: false,
        error: "Expected object, received null"
      });
      expect(recordSchema.validate(undefined)).to.deep.equal({
        success: false,
        error: "Expected object, received undefined"
      });
    });
    it("should fail for invalid values", function () {
      expect(recordSchema.validate({
        a: "string"
      })).to.deep.equal({
        success: false,
        error: "Expected number, received string at key a"
      });
    });
  });
  describe("optional", function () {
    var optionalStringSchema = MiniZod.string().optional();
    it("should validate undefined as valid", function () {
      expect(optionalStringSchema.validate(undefined)).to.deep.equal({
        success: true,
        value: undefined
      });
    });
    it("should validate valid string", function () {
      expect(optionalStringSchema.validate("hello")).to.deep.equal({
        success: true,
        value: "hello"
      });
    });
    it("should fail for invalid string values", function () {
      expect(optionalStringSchema.validate(123)).to.deep.equal({
        success: false,
        error: "Expected string, received number"
      });
    });
  });
  describe("nullable", function () {
    var nullableStringSchema = MiniZod.string().nullable();
    it("should validate null and undefined as valid", function () {
      expect(nullableStringSchema.validate(null)).to.deep.equal({
        success: true,
        value: null
      });
      expect(nullableStringSchema.validate(undefined)).to.deep.equal({
        success: true,
        value: undefined
      });
    });
    it("should validate valid string", function () {
      expect(nullableStringSchema.validate("hello")).to.deep.equal({
        success: true,
        value: "hello"
      });
    });
    it("should fail for invalid string values", function () {
      expect(nullableStringSchema.validate(123)).to.deep.equal({
        success: false,
        error: "Expected string, received number"
      });
    });
  });
});