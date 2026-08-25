"use strict";

var _require = require("../utils.js"),
  expectToThrow = _require.expectToThrow,
  expectToThrowSnapshot = _require.expectToThrowSnapshot,
  shouldBeSame = _require.shouldBeSame,
  createDocV4 = _require.createDocV4,
  captureLogs = _require.captureLogs,
  expect = _require.expect,
  getZip = _require.getZip;
var expressionParser = require("../../expressions.js");
var proofStateModule = require("../../proof-state-module.js");
var inspectModule = require("../../inspect-module.js");
var Docxtemplater = require("../../docxtemplater.js");
var _require2 = require("../../doc-utils.js"),
  pushArray = _require2.pushArray,
  traits = _require2.traits,
  uniq = _require2.uniq;
var fixDocPrCorruption = require("../../modules/fix-doc-pr-corruption.js");
function uniqTimes(arr) {
  var times = {},
    result = [];
  for (var _i2 = 0; _i2 < arr.length; _i2++) {
    var el = arr[_i2];
    if (times[el] == null) {
      times[el] = 0;
      result.push([el]);
    }
    times[el] += 1;
  }
  for (var _i4 = 0; _i4 < result.length; _i4++) {
    var item = result[_i4];
    item[1] = times[item[0]];
  }
  return result;
}
describe("Verify apiversion", function () {
  it("should work with valid api version", function () {
    var module = {
      name: "Mymod",
      requiredAPIVersion: "3.23.0",
      render: function render(part) {
        return part.value;
      }
    };
    createDocV4("tag-example.docx", {
      modules: [module]
    });
  });
  it("should fail with invalid api version", function () {
    var module = {
      name: "Mymod",
      requiredAPIVersion: "3.92.0",
      render: function render(part) {
        return part.value;
      }
    };
    expectToThrowSnapshot(function () {
      return createDocV4("loop-valid.docx", {
        modules: [module]
      });
    });
  });
  it("should fail when trying to attach null module", function () {
    expectToThrow(function () {
      return new Docxtemplater(getZip("loop-valid.docx"), {
        modules: [null]
      });
    }, Error, {
      message: "Cannot attachModule with a falsy value",
      name: "InternalError",
      properties: {}
    });
  });
});
describe("Module attachment", function () {
  it("should not allow to attach the same module twice", function () {
    var module = {
      name: "TestModule",
      requiredAPIVersion: "3.0.0",
      render: function render(part) {
        return part.value;
      }
    };
    createDocV4("loop-valid.docx", {
      modules: [module]
    });
    var errMessage = null;
    try {
      createDocV4("tag-example.docx", {
        modules: [module]
      });
    } catch (e) {
      errMessage = e.message;
    }
    expect(errMessage).to.equal('Cannot attach a module that was already attached : "TestModule". The most likely cause is that you are instantiating the module at the root level, and using it for multiple instances of Docxtemplater');
  });
  it("should allow to attach the same module twice if it has a clone method", function () {
    var module = {
      name: "TestModule",
      requiredAPIVersion: "3.0.0",
      clone: function clone() {
        return this;
      },
      render: function render(part) {
        return part.value;
      }
    };
    createDocV4("loop-valid.docx", {
      modules: [module]
    });
    createDocV4("tag-example.docx", {
      modules: [module]
    });
    createDocV4("tag-example.docx", {
      modules: [module]
    });
  });
  it("should automatically detach inspect module", function () {
    var imodule = inspectModule();
    createDocV4("loop-valid.docx", {
      modules: [imodule]
    }).render();
    createDocV4("loop-valid.docx", {
      modules: [imodule]
    }).render();
  });
});
describe("Module xml parse", function () {
  it("should not mutate options (regression for issue #526)", function () {
    var module = {
      name: "FooModule",
      requiredAPIVersion: "3.0.0",
      optionsTransformer: function optionsTransformer(options, docxtemplater) {
        var relsFiles = docxtemplater.zip.file(/document.xml.rels/).map(function (file) {
          return file.name;
        });
        pushArray(options.xmlFileNames, relsFiles);
        return options;
      }
    };
    var opts = {
      modules: [module]
    };
    createDocV4("tag-example.docx", opts);
    delete opts.modules;
    expect(opts).to.deep.equal({});
  });
  it("should be possible to parse xml files : xmlFileNames.push() without side effect fixed since v3.55.0", function () {
    var xmlDocuments;
    var module = {
      name: "ParseXMLModule",
      requiredAPIVersion: "3.0.0",
      set: function set(options) {
        if (options.xmlDocuments) {
          xmlDocuments = options.xmlDocuments;
        }
      },
      optionsTransformer: function optionsTransformer(options, docxtemplater) {
        var relsFiles = docxtemplater.zip.file(/document.xml.rels/).map(function (_ref) {
          var name = _ref.name;
          return name;
        });

        /*
         * This part tests that you can mutate the options here without
         * mutating it for future documents
         * Fixed since 3.55.0
         */
        pushArray(options.xmlFileNames, relsFiles);
        return options;
      }
    };
    var doc = createDocV4("tag-example.docx", {
      modules: [module]
    });
    expect(Object.keys(xmlDocuments)).to.deep.equal(["[Content_Types].xml", "word/_rels/document.xml.rels"]);
    var rels = xmlDocuments["word/_rels/document.xml.rels"].getElementsByTagName("Relationship");
    expect(rels.length).to.equal(10);
    rels[5].setAttribute("Foobar", "Baz");
    doc.render();
    shouldBeSame({
      doc: doc,
      expectedName: "expected-module-change-rels.docx"
    });
  });
});
describe("Module unique tags xml", function () {
  it("should not cause an issue if tagsXmlLexedArray contains duplicates", function () {
    var module = {
      name: "FooModule",
      requiredAPIVersion: "3.0.0",
      optionsTransformer: function optionsTransformer(options, docxtemplater) {
        docxtemplater.fileTypeConfig.tagsXmlLexedArray.push("w:p", "w:r", "w:p");
        return options;
      }
    };
    var doc = createDocV4("tag-example.docx", {
      modules: [module]
    });
    doc.render({
      first_name: "Hipp",
      last_name: "Edgar",
      phone: "0652455478",
      description: "New Website"
    });
    shouldBeSame({
      doc: doc,
      expectedName: "expected-tag-example.docx"
    });
  });
});
describe("Module traits", function () {
  it("should not cause an issue if using traits.expandTo containing loop", function () {
    var moduleName = "comment-module";
    function getInner(_ref2) {
      var part = _ref2.part,
        leftParts = _ref2.leftParts,
        rightParts = _ref2.rightParts,
        postparse = _ref2.postparse;
      part.subparsed = postparse([].concat(leftParts).concat(rightParts), {
        basePart: part
      });
      return part;
    }
    var module = {
      name: "Test module",
      requiredAPIVersion: "3.0.0",
      parse: function parse(placeHolderContent) {
        if (placeHolderContent[0] === "£") {
          var type = "placeholder";
          return {
            type: type,
            value: placeHolderContent.substr(1),
            module: moduleName
          };
        }
      },
      postparse: function postparse(parsed, _ref3) {
        var postparse = _ref3.postparse;
        parsed = traits.expandToOne(parsed, {
          moduleName: moduleName,
          getInner: getInner,
          expandTo: ["w:p"],
          postparse: postparse
        });
        return parsed;
      },
      render: function render(part) {
        if (part.module === moduleName) {
          return {
            value: ""
          };
        }
      }
    };
    var doc = createDocV4("comment-with-loop.docx", {
      modules: [module]
    }).render({});
    shouldBeSame({
      doc: doc,
      expectedName: "expected-comment-example.docx"
    });
  });
});
describe("Module errors", function () {
  it("should pass the errors to errorsTransformer", function () {
    var moduleName = "ErrorModule";
    var catched = null;
    var myErrors = [];
    var module = {
      name: "Error module",
      requiredAPIVersion: "3.0.0",
      parse: function parse(placeHolderContent) {
        var type = "placeholder";
        return {
          type: type,
          value: placeHolderContent,
          module: moduleName
        };
      },
      errorsTransformer: function errorsTransformer(errors) {
        pushArray(myErrors, errors);
        var result = [];
        for (var _i6 = 0; _i6 < errors.length; _i6++) {
          var e = errors[_i6];
          e.xyz = "xxx";
          result.push(e);
        }
        return result;
      },
      render: function render(part) {
        if (part.module === moduleName) {
          return {
            errors: [new Error("foobar ".concat(part.value))]
          };
        }
      }
    };
    var doc = createDocV4("tag-example.docx", {
      modules: [module]
    });
    var capture = captureLogs();
    try {
      doc.render();
    } catch (e) {
      catched = e;
    }
    capture.stop();
    expect(catched.properties.errors[0].xyz).to.equal("xxx");
    expect(myErrors.length).to.equal(9);
    expect(myErrors[0].message).to.equal("foobar last_name");
  });
  it("should log the error that is returned from render", function () {
    var moduleName = "ErrorModule";
    var module = {
      name: "Error module",
      requiredAPIVersion: "3.0.0",
      parse: function parse(placeHolderContent) {
        var type = "placeholder";
        return {
          type: type,
          value: placeHolderContent,
          module: moduleName
        };
      },
      render: function render(part) {
        if (part.module === moduleName) {
          return {
            errors: [new Error("foobar ".concat(part.value))]
          };
        }
      }
    };
    var error = null;
    var doc = createDocV4("tag-example.docx", {
      modules: [module]
    });
    var capture = captureLogs();
    try {
      doc.render();
    } catch (e) {
      error = e;
    }
    capture.stop();
    expect(error).to.be.an("object");
    expect(error.message).to.equal("Multi error");
    expect(error.properties.errors.length).to.equal(9);
    expect(error.properties.errors[4].properties.file).to.equal("word/document.xml");
    expect(error.properties.errors[4].message).to.equal("foobar last_name");
    expect(error.properties.errors[5].message).to.equal("foobar first_name");
    // expect(error.properties.errors[2].message).to.equal("foobar phone");

    var logs = capture.logs();
    expect(logs.length).to.equal(1, "Incorrect logs count");
    expect(logs[0]).to.contain("foobar last_name");
    expect(logs[0]).to.contain("foobar first_name");
    expect(logs[0]).to.contain("foobar phone");
    expect(logs[0]).to.satisfy(function (log) {
      return (
        // for chrome
        log.indexOf(".render") !== -1 ||
        // for firefox
        log.indexOf("render@") !== -1 ||
        // for bun (https://bun.sh/)
        log.indexOf("render (") !== -1
      );
    });
    var parsedLog = JSON.parse(logs[0]);
    expect(parsedLog.error.length).to.equal(9);
    expect(error.properties.errors[0].properties.file).to.equal("word/header1.xml");
    expect(error.properties.errors[0].message).to.equal("foobar last_name");
    expect(error.properties.errors[1].message).to.equal("foobar first_name");
    expect(error.properties.errors[2].message).to.equal("foobar phone");
    expect(error.properties.errors[6].properties.file).to.equal("word/footer1.xml");
    expect(error.properties.errors[6].message).to.equal("foobar last_name");
  });
  it("should throw specific error if adding same module twice", function () {
    var mod1 = {
      name: "TestModule",
      set: function set() {
        return null;
      }
    };
    var mod2 = {
      name: "TestModule",
      set: function set() {
        return null;
      }
    };

    // This test will test the case where the fixDocPrCorruption is used on two different instances of the docxtemplater library
    expectToThrow(function () {
      return createDocV4("loop-image-footer.docx", {
        modules: [mod1, mod2]
      });
    }, Error, {
      message: 'Detected duplicate module "TestModule"',
      name: "InternalError",
      properties: {}
    });
  });
});
describe("Module should pass options to module.parse, module.postparse, module.render, module.postrender", function () {
  it("should pass filePath and contentType options", function () {
    var filePaths = [],
      relsType = [],
      ct = [];
    var renderFP = "",
      renderCT = "",
      postrenderFP = "",
      postrenderCT = "",
      postparseFP = "",
      postparseCT = "";
    var module = {
      name: "Test module",
      requiredAPIVersion: "3.0.0",
      parse: function parse(a, options) {
        filePaths.push(options.filePath);
        ct.push(options.contentType);
        relsType.push(options.relsType);
      },
      postparse: function postparse(a, options) {
        postparseFP = options.filePath;
        postparseCT = options.contentType;
        return a;
      },
      render: function render(a, options) {
        renderFP = options.filePath;
        renderCT = options.contentType;
      },
      postrender: function postrender(a, options) {
        postrenderFP = options.filePath;
        postrenderCT = options.contentType;
        return a;
      }
    };
    createDocV4("tag-example.docx", {
      modules: [module]
    }).render({});
    expect(renderFP).to.equal("word/footnotes.xml");
    expect(renderCT).to.equal("application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml");
    expect(postparseFP).to.equal("word/footnotes.xml");
    expect(postparseCT).to.equal("application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml");
    expect(postrenderFP).to.equal("word/footnotes.xml");
    expect(postrenderCT).to.equal("application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml");

    /*
     * The order of the filePaths here is important, this has been fixed in
     * version 3.37.8 : First headers are templated, than the document,
     * than the footers.
     */
    expect(filePaths).to.deep.equal([
    // Header appears 4 times because there are 4 tags in the header
    "word/header1.xml", "word/header1.xml", "word/header1.xml", "word/header1.xml",
    // Document appears 2 times because there are 2 tags in the header
    "word/document.xml", "word/document.xml",
    // Footer appears 3 times because there are 3 tags in the header
    "word/footer1.xml", "word/footer1.xml", "word/footer1.xml"]);
    expect(ct).to.deep.equal(["application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"]);
    expect(relsType).to.deep.equal([undefined,
    // match to header1.xml
    undefined,
    // match to header1.xml
    undefined,
    // match to header1.xml
    undefined,
    // match to header1.xml
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    // match to document.xml
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    // match to document.xml
    undefined,
    // match to footer1.xml
    undefined,
    // match to footer1.xml
    undefined // match to footer1.xml
    ]);
  });
});
describe("Module detachment", function () {
  it("should detach the module when the module does not support the document filetype", function () {
    var isModuleCalled = false;
    var isDetachedCalled = false;
    var module = {
      optionsTransformer: function optionsTransformer(options) {
        isModuleCalled = true;
        return options;
      },
      on: function on(eventName) {
        if (eventName === "detached") {
          isDetachedCalled = true;
        }
      },
      supportedFileTypes: ["pptx"]
    };
    createDocV4("tag-example.docx", {
      modules: [module]
    });
    expect(isDetachedCalled).to.equal(true);
    expect(isModuleCalled).to.equal(false);
  });
});
describe("Module Matcher API", function () {
  it("should call onMatch function", function () {
    function module1() {
      var myVal = "";
      return {
        name: "module1",
        matchers: function matchers() {
          return [["l", "module-m1", {
            onMatch: function onMatch(part) {
              myVal = part.prefix + part.lIndex + "!!";
            }
          }]];
        },
        render: function render(part) {
          if (part.module === "module-m1") {
            return {
              value: myVal
            };
          }
        }
      };
    }
    expect(this.renderV4({
      name: "tag-example.docx",
      expectedText: "l29!! John",
      data: {
        first_name: "John"
      },
      options: {
        modules: [module1()]
      }
    }));
  });
  it("should automatically choose module with longest value", function () {
    function module1() {
      return {
        name: "module1",
        matchers: function matchers() {
          return [["l", "module-m1"]];
        },
        render: function render(part) {
          if (part.module === "module-m1") {
            return {
              value: part.value
            };
          }
        }
      };
    }
    function module2() {
      return {
        name: "module2",
        matchers: function matchers() {
          return [[/last_(.*)/, "module-m2"]];
        },
        render: function render(part) {
          if (part.module === "module-m2") {
            return {
              value: part.value
            };
          }
        }
      };
    }
    function module3() {
      return {
        name: "module3",
        matchers: function matchers() {
          return [["last", "module-m3"]];
        },
        render: function render(part) {
          if (part.module === "module-m3") {
            return {
              value: part.value
            };
          }
        }
      };
    }
    expect(createDocV4("tag-example.docx", {
      modules: [module1(), module2(), module3()]
    }).render({
      first_name: "John"
    }).getFullText()).to.equal("name John");
    expect(createDocV4("tag-example.docx", {
      modules: [module3(), module2(), module1()]
    }).render({
      first_name: "John"
    }).getFullText()).to.equal("name John");
  });
});
describe("Fix doc pr corruption module", function () {
  it("should work on multiple instances in parallel (in footer)", function () {
    var doc = createDocV4("loop-image-footer.docx", {
      modules: [fixDocPrCorruption]
    });
    // This test will test the case where the fixDocPrCorruption is used on two different instances of the docxtemplater library
    createDocV4("tag-example.docx", {
      modules: [fixDocPrCorruption]
    });
    return doc.renderAsync({
      loop: [1, 2, 3, 4]
    }).then(function () {
      shouldBeSame({
        doc: doc,
        expectedName: "expected-loop-images-footer.docx"
      });
    });
  });
});
describe("Proofstate module", function () {
  it("should work with angular parser with proofstate module", function () {
    shouldBeSame({
      doc: createDocV4("angular-example.docx", {
        parser: expressionParser,
        modules: [proofStateModule]
      }).render({
        person: {
          first_name: "Hipp",
          last_name: "Edgar",
          birth_year: 1955,
          age: 59
        }
      }),
      expectedName: "expected-proofstate-removed.docx"
    });
  });
});
describe("Module calls to on(eventName) to pass events", function () {
  it("should work with v4 synchronously", function () {
    var calls = [];
    var mod = {
      name: "TestModule",
      on: function on(eventName) {
        calls.push(eventName);
      }
    };
    createDocV4("loop-image-footer.docx", {
      modules: [mod]
    }).render({
      loop: [1, 2, 3, 4]
    });
    expect(calls).to.deep.equal(["attached", "before-preparse", "after-preparse", "after-parse", "after-postparse", "syncing-zip", "synced-zip"]);
  });
});
describe("Module call order", function () {
  it("should work with v4 synchronously", function () {
    var calls = [];
    var mod = {
      name: "TestModule",
      on: function on() {
        calls.push("on");
      },
      set: function set() {
        calls.push("set");
        return null;
      },
      getFileType: function getFileType(_ref4) {
        var doc = _ref4.doc;
        doc.targets.unshift("word/document.xml");
        calls.push("getFileType");
      },
      optionsTransformer: function optionsTransformer(options) {
        calls.push("optionsTransformer");
        return options;
      },
      preparse: function preparse() {
        calls.push("preparse");
        return null;
      },
      matchers: function matchers() {
        calls.push("matchers");
        return [];
      },
      parse: function parse() {
        calls.push("parse");
        return null;
      },
      getTraits: function getTraits() {
        calls.push("getTraits");
      },
      postparse: function postparse() {
        calls.push("postparse");
        return null;
      },
      errorsTransformer: function errorsTransformer() {
        calls.push("errorsTransformer");
      },
      resolve: function resolve() {
        calls.push("resolve");
      },
      getRenderedMap: function getRenderedMap(obj) {
        calls.push("getRenderedMap");
        return obj;
      },
      render: function render() {
        calls.push("render");
        return null;
      },
      nullGetter: function nullGetter() {
        calls.push("nullGetter");
      },
      postrender: function postrender() {
        calls.push("postrender");
        return [];
      }
    };
    var doc = createDocV4("tag-example.docx", {
      modules: [mod]
    });
    var uniqCalls = uniq(calls);
    expect(uniqCalls).to.deep.equal([
    // Before render
    "on", "set", "getFileType", "optionsTransformer", "preparse", "matchers", "parse", "getTraits", "postparse", "errorsTransformer"]);
    var uCallCount = uniqCalls.length;
    doc.render({
      loop: [1, 2, 3, 4]
    });
    expect(uniq(calls).slice(uCallCount)).to.deep.equal([
    // After render :
    "getRenderedMap", "render", "nullGetter", "postrender"]);
  });
  it("should work with v4 async", function () {
    var calls = [],
      parseValues = [],
      preparsedFilePaths = [];
    var mod = {
      name: "TestModule",
      on: function on() {
        calls.push("on");
      },
      set: function set() {
        calls.push("set");
        return null;
      },
      getFileType: function getFileType() {
        calls.push("getFileType");
      },
      optionsTransformer: function optionsTransformer(options) {
        calls.push("optionsTransformer");
        return options;
      },
      preparse: function preparse(_, options) {
        preparsedFilePaths.push(options.filePath);
        calls.push("preparse");
        return null;
      },
      matchers: function matchers() {
        calls.push("matchers");
        return [];
      },
      parse: function parse(part) {
        parseValues.push(part);
        calls.push("parse");
        return null;
      },
      getTraits: function getTraits() {
        calls.push("getTraits");
      },
      postparse: function postparse() {
        calls.push("postparse");
        return null;
      },
      errorsTransformer: function errorsTransformer() {
        calls.push("errorsTransformer");
      },
      resolve: function resolve() {
        calls.push("resolve");
      },
      getRenderedMap: function getRenderedMap(obj) {
        calls.push("getRenderedMap");
        return obj;
      },
      render: function render() {
        calls.push("render");
        return null;
      },
      nullGetter: function nullGetter() {
        calls.push("nullGetter");
      },
      postrender: function postrender() {
        calls.push("postrender");
        return [];
      }
    };
    return createDocV4("tag-example.docx", {
      modules: [mod]
    }).renderAsync({
      loop: [1, 2, 3, 4]
    }).then(function () {
      expect(parseValues).to.deep.equal(["last_name", "first_name", "phone", "description", "last_name", "first_name", "last_name", "first_name", "phone"]);
      expect(parseValues.length).to.equal(9);
      expect(preparsedFilePaths).to.deep.equal(["word/settings.xml", "docProps/core.xml", "docProps/app.xml", "word/header1.xml", "word/document.xml", "word/footer1.xml", "word/footnotes.xml"]);
      expect(preparsedFilePaths.length).to.equal(7);
      expect(uniqTimes(calls)).to.deep.equal([
      // Runs on("attached") (module is attached), after-preparse, ...
      ["on", 7],
      // Runs multiple times to set xmllexed, filePath, parsed
      ["set", 62],
      /*
       * Runs Twice, it should theoretically run once
       * #tofix-getFileType-twice . However for some modules, if
       * you run it just once, the modules break (this is in
       * particular if you use const doc = new Docxtemplater();
       * doc.attachModule() which is now deprecated
       */
      ["getFileType", 2],
      // Runs Once
      ["optionsTransformer", 1],
      // Runs for each templatedFile
      ["preparse", 7],
      // Runs for each tag
      ["matchers", 9],
      // Runs for each tag
      ["parse", 9],
      // Runs for each templatedFile
      ["getTraits", 7],
      // Runs for each templatedFile
      ["postparse", 7],
      // Runs for each templatedFile
      ["errorsTransformer", 7],
      // Runs Once
      ["getRenderedMap", 1],
      // Runs for each tag * data
      ["resolve", 9],
      // Runs for each tag * data
      ["nullGetter", 9],
      // Runs for each xml tag or placeholder tag
      ["render", 242],
      // Runs for each templatedFile
      ["postrender", 7]]);
    });
  });
  it("should work with v3", function () {
    var calls = [];
    var mod = {
      name: "TestModule",
      on: function on() {
        calls.push("on");
      },
      set: function set() {
        calls.push("set");
        return null;
      },
      getFileType: function getFileType() {
        calls.push("getFileType");
      },
      optionsTransformer: function optionsTransformer(options) {
        calls.push("optionsTransformer");
        return options;
      },
      preparse: function preparse() {
        calls.push("preparse");
        return null;
      },
      matchers: function matchers() {
        calls.push("matchers");
        return [];
      },
      parse: function parse() {
        calls.push("parse");
        return null;
      },
      getTraits: function getTraits() {
        calls.push("getTraits");
      },
      postparse: function postparse() {
        calls.push("postparse");
        return null;
      },
      errorsTransformer: function errorsTransformer() {
        calls.push("errorsTransformer");
      },
      resolve: function resolve() {
        calls.push("on");
      },
      getRenderedMap: function getRenderedMap(obj) {
        calls.push("getRenderedMap");
        return obj;
      },
      render: function render() {
        calls.push("render");
        return null;
      },
      nullGetter: function nullGetter() {
        calls.push("nullGetter");
      },
      postrender: function postrender() {
        calls.push("postrender");
        return [];
      }
    };
    this.render({
      name: "loop-image-footer.docx",
      data: {
        loop: [1, 2, 3, 4]
      },
      options: {
        modules: [mod]
      }
    });
    expect(uniq(calls)).to.deep.equal(["on", "set", "getFileType", "optionsTransformer", "preparse", "matchers", "getTraits", "postparse", "errorsTransformer", "getRenderedMap", "render", "postrender"]);
  });
});
describe("Module priority", function () {
  it("should reorder modules #test-reorder-modules", function () {
    var doc = createDocV4("loop-image-footer.docx", {
      modules: [{
        priority: 4,
        name: "M1",
        parse: function parse(parsed) {
          return parsed;
        }
      }, {
        priority: -1,
        name: "M2",
        parse: function parse(parsed) {
          return parsed;
        }
      }, {
        priority: 5,
        name: "M3",
        parse: function parse(parsed) {
          return parsed;
        }
      }, {
        priority: 5,
        name: "M4",
        parse: function parse(parsed) {
          return parsed;
        }
      }, {
        priority: 5,
        name: "M5",
        parse: function parse(parsed) {
          return parsed;
        }
      }]
    });
    var orderedNames = [];
    for (var _i8 = 0, _doc$modules2 = doc.modules; _i8 < _doc$modules2.length; _i8++) {
      var name = _doc$modules2[_i8].name;
      orderedNames.push(name);
    }
    expect(orderedNames).to.deep.equal(["M3",
    // Priority 5
    "M4",
    // Priority 5
    "M5",
    // Priority 5
    "M1",
    // Priority 4

    // All default modules have default priority of 0
    "LoopModule", "SpacePreserveModule", "ExpandPairTrait", "RawXmlModule", "Render", "Common", "AssertionModule", "M2" // Priority -1
    ]);
  });
});