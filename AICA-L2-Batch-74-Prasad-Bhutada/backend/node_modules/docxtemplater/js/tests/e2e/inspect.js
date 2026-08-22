"use strict";

var inspectModule = require("../../inspect-module.js");
var _require = require("../utils.js"),
  expectToThrowSnapshot = _require.expectToThrowSnapshot,
  createDocV4 = _require.createDocV4,
  expect = _require.expect,
  shouldBeSame = _require.shouldBeSame;
describe("Inspect module", function () {
  it("should get main tags", function () {
    var iModule = inspectModule();
    var doc = createDocV4("tag-loop-example.docx", {
      modules: [iModule]
    });
    expect(iModule.getStructuredTags()).to.matchSnapshot();
    expect(iModule.getTags()).to.be.deep.equal({
      offre: {
        nom: {},
        prix: {},
        titre: {}
      },
      nom: {},
      prenom: {}
    });
    var data = {
      offre: [{}],
      prenom: "John"
    };
    doc.render(data);
    var fi = iModule.fullInspected["word/document.xml"];
    var _fi$nullValues = fi.nullValues,
      summary = _fi$nullValues.summary,
      detail = _fi$nullValues.detail;
    var postparsed = fi.postparsed,
      parsed = fi.parsed,
      xmllexed = fi.xmllexed;
    expect(postparsed.length).to.equal(249);
    expect(parsed.length).to.equal(385);
    expect(xmllexed.length).to.equal(383);
    expect(iModule.inspect.tags).to.be.deep.equal(data);
    expect(detail).to.be.an("array");
    expect(detail[0].part.value).to.equal("nom");
    expect(detail[0].scopeManager.scopeList[0].prenom).to.equal("John");
    expect(summary).to.be.deep.equal([["offre", "nom"], ["offre", "prix"], ["offre", "titre"], ["nom"]]);
  });
  it("should get all tags (pptx file)", function () {
    var iModule = inspectModule();
    createDocV4("multi-page.pptx", {
      modules: [iModule]
    });
    expect(iModule.getStructuredTags()).to.matchSnapshot();
    expect(iModule.getFileType()).to.be.deep.equal("pptx");
    expect(iModule.getAllTags()).to.be.deep.equal({
      tag: {},
      users: {
        name: {}
      }
    });
    expect(iModule.getTemplatedFiles().sort()).to.be.deep.equal(["ppt/slides/slide1.xml", "ppt/slides/slide2.xml", "ppt/slideLayouts/slideLayout1.xml", "ppt/slideLayouts/slideLayout10.xml", "ppt/slideLayouts/slideLayout11.xml", "ppt/slideLayouts/slideLayout12.xml", "ppt/slideLayouts/slideLayout2.xml", "ppt/slideLayouts/slideLayout3.xml", "ppt/slideLayouts/slideLayout4.xml", "ppt/slideLayouts/slideLayout5.xml", "ppt/slideLayouts/slideLayout6.xml", "ppt/slideLayouts/slideLayout7.xml", "ppt/slideLayouts/slideLayout8.xml", "ppt/slideLayouts/slideLayout9.xml", "ppt/slideMasters/slideMaster1.xml", "ppt/presentation.xml", "docProps/app.xml", "docProps/core.xml"].sort());
  });
  it("should get all tags and merge them", function () {
    var iModule = inspectModule();
    createDocV4("multi-page-to-merge.pptx", {
      modules: [iModule]
    });
    expect(iModule.getAllTags()).to.be.deep.equal({
      tag: {},
      users: {
        name: {},
        age: {},
        company: {}
      }
    });
  });
  it("should get all tags with additional data, and then render correctly", function () {
    var iModule = inspectModule();
    var doc = createDocV4("tag-product-loop.docx", {
      modules: [iModule]
    });
    expect(iModule.getAllStructuredTags()).to.matchSnapshot();

    // Tests #regression-postparsed-after-inspect-modified
    doc.render({
      products: [{
        title: "Lorem",
        name: "ipsum",
        reference: "0000"
      }]
    });
    var expectedName = "expected-tag-product.docx";
    expect(doc.getFullText()).to.deep.equal("LoremProduct name : ipsumProduct reference : 0000");
    shouldBeSame({
      doc: doc,
      expectedName: expectedName
    });
  });
  it("should show throw error if calling getAllTags, getAllStructuredTags without attaching the module", function () {
    // Fixed since v3.67.5
    var iModule = inspectModule();
    expectToThrowSnapshot(function () {
      return iModule.getAllTags();
    });
    expectToThrowSnapshot(function () {
      return iModule.getTags();
    });
    expectToThrowSnapshot(function () {
      return iModule.getInspected();
    });
    expectToThrowSnapshot(function () {
      return iModule.getAllStructuredTags();
    });
    expectToThrowSnapshot(function () {
      return iModule.getTemplatedFiles();
    });
    expectToThrowSnapshot(function () {
      return iModule.getStructuredTags();
    });
  });
});