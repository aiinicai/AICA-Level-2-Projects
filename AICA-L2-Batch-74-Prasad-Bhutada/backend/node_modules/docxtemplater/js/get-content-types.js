"use strict";

var _require = require("./doc-utils.js"),
  str2xml = _require.str2xml;
var ctXML = "[Content_Types].xml";
function collectContentTypes(overrides, defaults, zip) {
  var partNames = {};
  for (var _i2 = 0; _i2 < overrides.length; _i2++) {
    var override = overrides[_i2];
    var contentType = override.getAttribute("ContentType");
    var partName = override.getAttribute("PartName").substr(1);
    partNames[partName] = contentType;
  }
  zip.file(/./).map(function (_ref) {
    var name = _ref.name;
    for (var _i4 = 0; _i4 < defaults.length; _i4++) {
      var def = defaults[_i4];
      var _contentType = def.getAttribute("ContentType");
      var extension = def.getAttribute("Extension");
      if (name.slice(name.length - extension.length) === extension && !partNames[name] && name !== ctXML) {
        partNames[name] = _contentType;
      }
    }
    partNames[name] || (partNames[name] = "");
  });
  return partNames;
}
function getContentTypes(zip) {
  var contentTypes = zip.files[ctXML];
  var contentTypeXml = contentTypes ? str2xml(contentTypes.asText()) : null;
  var overrides = contentTypeXml ? contentTypeXml.getElementsByTagName("Override") : null;
  var defaults = contentTypeXml ? contentTypeXml.getElementsByTagName("Default") : null;
  return {
    overrides: overrides,
    defaults: defaults,
    contentTypes: contentTypes,
    contentTypeXml: contentTypeXml
  };
}
module.exports = {
  collectContentTypes: collectContentTypes,
  getContentTypes: getContentTypes
};