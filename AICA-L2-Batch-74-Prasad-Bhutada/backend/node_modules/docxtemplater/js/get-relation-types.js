"use strict";

var _require = require("./doc-utils.js"),
  str2xml = _require.str2xml;
var relsFile = "_rels/.rels";
function getRelsTypes(zip) {
  var rootRels = zip.files[relsFile];
  var rootRelsXml = rootRels ? str2xml(rootRels.asText()) : null;
  var rootRelationships = rootRelsXml ? rootRelsXml.getElementsByTagName("Relationship") : [];
  var relsTypes = {};
  for (var _i2 = 0; _i2 < rootRelationships.length; _i2++) {
    var relation = rootRelationships[_i2];
    relsTypes[relation.getAttribute("Target")] = relation.getAttribute("Type");
  }
  return relsTypes;
}
module.exports = {
  getRelsTypes: getRelsTypes
};