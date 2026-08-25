"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var _require = require("./utils.js"),
  last = _require.last,
  first = _require.first;
function XTError(message) {
  this.name = "GenericError";
  this.message = message;
  this.stack = new Error(message).stack;
}
XTError.prototype = Error.prototype;
function XTTemplateError(message) {
  this.name = "TemplateError";
  this.message = message;
  this.stack = new Error(message).stack;
}
XTTemplateError.prototype = new XTError();
function XTRenderingError(message) {
  this.name = "RenderingError";
  this.message = message;
  this.stack = new Error(message).stack;
}
XTRenderingError.prototype = new XTError();
function XTScopeParserError(message) {
  this.name = "ScopeParserError";
  this.message = message;
  this.stack = new Error(message).stack;
}
XTScopeParserError.prototype = new XTError();
function XTInternalError(message) {
  this.name = "InternalError";
  this.properties = {
    explanation: "InternalError"
  };
  this.message = message;
  this.stack = new Error(message).stack;
}
XTInternalError.prototype = new XTError();
function XTAPIVersionError(message) {
  this.name = "APIVersionError";
  this.properties = {
    explanation: "APIVersionError"
  };
  this.message = message;
  this.stack = new Error(message).stack;
}
XTAPIVersionError.prototype = new XTError();

/*
 * Version/Compatibility Errors
 * ============================
 */

function throwApiVersionError(msg, properties) {
  var err = new XTAPIVersionError(msg);
  /*
   * This error arises when a recent module version necessitates a more
   * current version of the Docxtemplater core. Docxtemplater specifies an
   * "APIVersion," and if a module requires API Version 3.55 or higher,
   * but the Docxtemplater instance provides API 3.52, this error will
   * occur. To resolve this issue, please update to the latest version of
   * Docxtemplater.
   */
  err.properties = _objectSpread({
    id: "api_version_error"
  }, properties);
  throw err;
}
function throwFileTypeNotIdentified(zip) {
  var files = Object.keys(zip.files).slice(0, 10);
  var msg = "";
  if (files.length === 0) {
    msg = "Empty zip file";
  } else {
    msg = "Zip file contains : ".concat(files.join(","));
  }
  var err = new XTInternalError("The filetype for this file could not be identified, is this file corrupted ? ".concat(msg));
  /*
   * This error happens if you're creating Docxtemplater with a zip file, but that file is not recognized as a docx/pptx/xlsx or odt file.
   *
   * Note that xlsx files and odt files need a paid module to be templated.
   *
   * Other zip files (zip, odp, ods) will trigger the same error.
   */
  err.properties = {
    id: "filetype_not_identified",
    explanation: "The filetype for this file could not be identified, is this file corrupted ? ".concat(msg)
  };
  throw err;
}
function throwFileTypeNotHandled(fileType) {
  var err = new XTInternalError("The filetype \"".concat(fileType, "\" is not handled by Docxtemplater"));
  /*
   * This error happens if the filetype was recognized (xlsx, odt), but
   * without the correct module, this file cannot be templated
   */
  err.properties = {
    id: "filetype_not_handled",
    explanation: "The file you are trying to generate is of type \"".concat(fileType, "\", but only docx and pptx formats are handled"),
    fileType: fileType
  };
  throw err;
}

/*
 * Template Errors
 * ===============
 */

function throwMultiError(errors) {
  var err = new XTTemplateError("Multi error");
  /*
   * This error is an Error that contains all template errors.
   * It is a multi error because it contains all errors of the template in :
   * err.properties.errors.
   *
   * You can then map on each sub error like this :
   *
   * ```js
   * for (const err of error.properties.errors) {
   *   console.log(err.properties.explanation);
   * }
   * ```
   */
  err.properties = {
    errors: errors,
    id: "multi_error",
    explanation: "The template has multiple errors"
  };
  throw err;
}
function getUnopenedTagException(options) {
  var err = new XTTemplateError("Unopened tag");
  /*
   * This error happens if a tag is closed but not opened. For example with
   * the following template:
   *
   * ```docx
   * Hello name} !
   * ```
   */
  err.properties = {
    xtag: last(options.xtag.split(" ")),
    id: "unopened_tag",
    context: options.xtag,
    offset: options.offset,
    lIndex: options.lIndex,
    explanation: "The tag beginning with \"".concat(options.xtag.substr(0, 30), "\" is unopened")
  };
  return err;
}
function getDuplicateOpenTagException(options) {
  var err = new XTTemplateError("Duplicate open tag, expected one open tag");
  /*
   * This error happens with following template :
   *
   * ```docx
   * Hello {{name
   * ```
   */
  err.properties = {
    xtag: first(options.xtag.split(" ")),
    id: "duplicate_open_tag",
    context: options.xtag,
    offset: options.offset,
    lIndex: options.lIndex,
    explanation: "The tag beginning with \"".concat(options.xtag.substr(0, 30), "\" has duplicate open tags")
  };
  return err;
}
function getDuplicateCloseTagException(options) {
  var err = new XTTemplateError("Duplicate close tag, expected one close tag");
  /*
   * This error happens with following template :
   *
   * ```docx
   * Hello {name}}
   * ```
   */
  err.properties = {
    xtag: first(options.xtag.split(" ")),
    id: "duplicate_close_tag",
    context: options.xtag,
    offset: options.offset,
    lIndex: options.lIndex,
    explanation: "The tag ending with \"".concat(options.xtag.substr(0, 30), "\" has duplicate close tags")
  };
  return err;
}
function getUnclosedTagException(options) {
  var err = new XTTemplateError("Unclosed tag");
  /*
   * This error happens if a tag is opened but not closed.
   * For example with the following template:
   *
   * ```docx
   * Hello {name !
   * ```
   */
  err.properties = {
    xtag: first(options.xtag.split(" ")).substr(1),
    // name
    id: "unclosed_tag",
    context: options.xtag,
    offset: options.offset,
    lIndex: options.lIndex,
    explanation: "The tag beginning with \"".concat(options.xtag.substr(0, 30), "\" is unclosed")
  };
  return err;
}
function throwXmlTagNotFound(options) {
  if (options.position === "left") {
    throwXmlTagNotFoundLeft(options);
  } else {
    throwXmlTagNotFoundRight(options);
  }
}

/*
 * Raw XML / XML Expansion Errors
 * ==============================
 */

function throwXmlTagNotFoundLeft(options) {
  var err = new XTTemplateError("No tag \"".concat(options.element, "\" was found at the ").concat(options.position));
  var part = options.parsed[options.index];
  /*
   * This error is not directly linked to the template, it means that some
   * tag tried to expand to adjacent XML tags, but those elements cannot be
   * accessed from the current node.
   *
   * This error happens if a rawXMLTag doesn't find a `<w:p>` element
   *
   * ```docx
   * <w:p><w:t>{@raw}</w:t>
   * // Note  that the `</w:p>` tag is missing.
   * ```
   */
  err.properties = {
    id: "no_xml_tag_found_at_left",
    explanation: "No tag \"".concat(options.element, "\" was found at the left"),
    offset: part.offset,
    part: part,
    parsed: options.parsed,
    index: options.index,
    element: options.element
  };
  throw err;
}
function throwXmlTagNotFoundRight(options) {
  var err = new XTTemplateError("No tag \"".concat(options.element, "\" was found at the ").concat(options.position));
  var part = options.parsed[options.index];
  /*
   * This error is not directly linked to the template, it means that some
   * tag tried to expand to adjacent XML tags, but those elements cannot be
   * accessed from the current node.
   */
  err.properties = {
    id: "no_xml_tag_found_at_right",
    explanation: "No tag \"".concat(options.element, "\" was found at the right"),
    offset: part.offset,
    part: part,
    parsed: options.parsed,
    index: options.index,
    element: options.element
  };
  throw err;
}
function getCorruptCharactersException(_ref) {
  var tag = _ref.tag,
    value = _ref.value,
    offset = _ref.offset;
  var err = new XTRenderingError("There are some XML corrupt characters");
  /*
   * This error prevents the docx document to become corrupt.
   * It happens if you're trying to render text that would produce invalid XML output.
   *
   * See #corrupt-character-error on how this can be fixed by changing your parser.
   */
  err.properties = {
    id: "invalid_xml_characters",
    xtag: tag,
    value: value,
    offset: offset,
    explanation: "There are some corrupt characters for the field \"".concat(tag, "\"")
  };
  return err;
}
function getInvalidRawXMLValueException(_ref2) {
  var tag = _ref2.tag,
    value = _ref2.value,
    offset = _ref2.offset,
    partDelims = _ref2.partDelims;
  var err = new XTRenderingError("Non string values are not allowed for rawXML tags");
  /*
   * This error happens if you try to render a rawXml tag, such as : {@raw}
   * And the value of the data for "raw" is truthy but not a string.
   *
   * (If the value of the data is falsy, than the tag is simply dropped and
   * no error is thrown)
   */
  err.properties = {
    id: "invalid_raw_xml_value",
    xtag: tag,
    value: value,
    offset: offset,
    explanation: "The value of the raw tag : \"".concat(partDelims, "\" is not a string")
  };
  return err;
}
function throwExpandNotFound(options) {
  var _options$part = options.part,
    value = _options$part.value,
    offset = _options$part.offset,
    _options$id = options.id,
    id = _options$id === void 0 ? "raw_tag_outerxml_invalid" : _options$id,
    _options$message = options.message,
    message = _options$message === void 0 ? "Raw tag not in paragraph" : _options$message;
  var part = options.part;
  var _options$explanation = options.explanation,
    explanation = _options$explanation === void 0 ? "The tag \"".concat(value, "\" is not inside a paragraph") : _options$explanation;
  if (typeof explanation === "function") {
    explanation = explanation(part);
  }
  /*
   * This error happens if you try to render a rawXml tag, such as : {@raw},
   * but that tag is not placed inside a paragraph.
   */
  var err = new XTTemplateError(message);
  err.properties = {
    id: id,
    explanation: explanation,
    rootError: options.rootError,
    xtag: value,
    offset: offset,
    postparsed: options.postparsed,
    expandTo: options.expandTo,
    index: options.index
  };
  throw err;
}
function throwRawTagShouldBeOnlyTextInParagraph(options) {
  var err = new XTTemplateError("Raw tag should be the only text in paragraph");
  var tag = options.part.value;
  /*
   * This happens when a rawXMLTag {@raw} is not the only text in the
   * paragraph. For example, writing ` {@raw}` (Note the spaces)
   * is not acceptable because the {@raw} tag replaces the full paragraph. We
   * prefer to throw an Error now rather than have "strange behavior"
   * because the spaces "disappeared".
   *
   * To correct this error, you have to add manually the text that you want
   * in your raw tag. (Or you can use the [Docxtemplater word-run
   * module](/modules/word-run/) which adds a tag
   * that can replace rawXML inside a tag).
   *
   * Writing
   *
   * ```docx
   * {@my_first_tag}{my_second_tag}
   * ```
   *
   * Or even
   *
   * ```docx
   * Hello {@my_first_tag}
   * ```
   *
   * Is misusing Docxtemplater.
   *
   * The `@` at the beginning means "replace the xml of **the
   * current paragraph** with scope.my_first_tag" so that means that
   * everything else in that Paragraph will be removed.
   */
  err.properties = {
    id: "raw_xml_tag_should_be_only_text_in_paragraph",
    explanation: "The raw tag \"".concat(tag, "\" should be the only text in this paragraph. This means that this tag should not be surrounded by any text or spaces."),
    xtag: tag,
    offset: options.part.offset,
    paragraphParts: options.paragraphParts
  };
  throw err;
}

/*
 * Loop / Table Structure Errors
 * =============================
 */

function getUnmatchedLoopException(part) {
  var location = part.location,
    offset = part.offset,
    square = part.square;
  var t = location === "start" ? "unclosed" : "unopened";
  var T = location === "start" ? "Unclosed" : "Unopened";
  var err = new XTTemplateError("".concat(T, " loop"));
  var tag = part.value;
  /*
   * This error happens with following template :
   *
   * ```docx
   * {#users}
   * {/companies}
   * ```
   */
  err.properties = {
    id: "".concat(t, "_loop"),
    explanation: "The loop with tag \"".concat(tag, "\" is ").concat(t),
    xtag: tag,
    offset: offset
  };
  if (square) {
    err.properties.square = square;
  }
  return err;
}
function getUnbalancedLoopException(pair, lastPair) {
  var err = new XTTemplateError("Unbalanced loop tag");
  var lastL = lastPair[0].part.value;
  var lastR = lastPair[1].part.value;
  var l = pair[0].part.value;
  var r = pair[1].part.value;
  /*
   * This error happens if you create a table and misplace tags inside the table :
   *
   * ```docx-md
   * | Head1    | Head2         |
   * | -------- | ------------  |
   * | {#a}X    | {/a}{#b}Y{/b} |
   * ```
   *
   *  In the case above, the {#a} and {/a} will expand to the whole loop, but this is not possible because of the other loop in {#b}Y{/b}
   *
   *  Instead, you should usually write :
   *
   * ```docx-md
   * | Head1    | Head2         |
   * | -------- | ------------  |
   * | {#a}X    | {#b}Y{/b}{/a} |
   * ```
   */
  err.properties = {
    id: "unbalanced_loop_tags",
    explanation: "Unbalanced loop tags {#".concat(lastL, "}{/").concat(lastR, "}{#").concat(l, "}{/").concat(r, "}"),
    offset: [lastPair[0].part.offset, pair[1].part.offset],
    lastPair: {
      left: lastPair[0].part.value,
      right: lastPair[1].part.value
    },
    pair: {
      left: pair[0].part.value,
      right: pair[1].part.value
    }
  };
  return err;
}
function getClosingTagNotMatchOpeningTag(_ref3) {
  var tags = _ref3.tags;
  var err = new XTTemplateError("Closing tag does not match opening tag");
  /*
   * This error happens if your loop tags are incorrectly closed
   *
   * ```docx
   * {#condition1}
   * Some text
   * {/otherCondition}
   * ```
   *
   * Since the start tag does not match the open tag, the template is invalid.
   */
  err.properties = {
    id: "closing_tag_does_not_match_opening_tag",
    explanation: "The tag \"".concat(tags[0].value, "\" is closed by the tag \"").concat(tags[1].value, "\""),
    openingtag: first(tags).value,
    offset: [first(tags).offset, last(tags).offset],
    closingtag: last(tags).value
  };
  if (first(tags).square) {
    err.properties.square = [first(tags).square, last(tags).square];
  }
  return err;
}
function getLoopPositionProducesInvalidXMLError(_ref4) {
  var tag = _ref4.tag,
    offset = _ref4.offset;
  var err = new XTTemplateError("The position of the loop tags \"".concat(tag, "\" would produce invalid XML"));
  /*
   * This happens when a loop would produce invalid XML.
   *
   * For example, if you write:
   *
   * ```docx-md
   * | Head1    | Head2         |
   * | -------- | ------------  |
   * | {#users} | content       |
   *
   * {/users}
   * ```
   *
   * this is not allowed since a loop that starts in a table must also end
   * in that table.
   */
  err.properties = {
    xtag: tag,
    id: "loop_position_invalid",
    explanation: "The tags \"".concat(tag, "\" are misplaced in the document, for example one of them is in a table and the other one outside the table"),
    offset: offset
  };
  return err;
}

/*
 * Scope Parser Errors
 * ===================
 */

function getScopeCompilationError(_ref5) {
  var tag = _ref5.tag,
    rootError = _ref5.rootError,
    offset = _ref5.offset;
  var err = new XTScopeParserError("Scope parser compilation failed");
  /*
   * This happens when your parser throws an error during compilation. The
   * parser is the second argument of the constructor
   * `new Docxtemplater(zip, {parser: function parser(tag) {}});`
   *
   * For example, if your template is:
   *
   * ```docx
   * {name++}
   * ```
   *
   * and you use the angular expression parser, you will have this error. The error
   * happens when you call parser('name++'); The underlying error can be
   * read in `e.properties.rootError`
   */
  err.properties = {
    id: "scopeparser_compilation_failed",
    offset: offset,
    xtag: tag,
    explanation: "The scope parser for the tag \"".concat(tag, "\" failed to compile"),
    rootError: rootError
  };
  return err;
}
function getScopeParserExecutionError(_ref6) {
  var tag = _ref6.tag,
    scope = _ref6.scope,
    error = _ref6.error,
    offset = _ref6.offset;
  var err = new XTScopeParserError("Scope parser execution failed");
  /*
   * This happens when your parser throws an error during execution. The
   * parser is the second argument of the constructor
   * `new Docxtemplater(zip, {parser: function parser(tag) {}});`
   *
   * For example, if your template is:
   *
   * ```docx
   * {test | toFixed}
   * ```
   *
   * and your code is :
   *
   * ```js
   * const expressionParser = require("docxtemplater/expressions.js");
   * const doc = new Docxtemplater(zip, {
   *   paragraphLoop: true,
   *   linebreaks: true,
   *   parser: expressionParser.configure({
   *     filters: {
   *       toFixed(input) {
   *         return input.toFixed();
   *       }
   *     }
   *   }),
   * });
   * doc.render({
   *   test: false
   * });
   * ```
   *
   * Since false.toFixed() triggers an error in Javascript, this will then throw an error "Scope parser execution failed".
   *
   * You can either fix your data or make your toFixed function more robust
   * by returning "input" if the input is not a number.
   */
  err.properties = {
    id: "scopeparser_execution_failed",
    explanation: "The scope parser for the tag \"".concat(tag, "\" failed to execute"),
    scope: scope,
    offset: offset,
    xtag: tag,
    rootError: error
  };
  return err;
}

/*
 * Internal / API Misuse Errors
 * ============================
 */

function throwUnimplementedTagType(part, index) {
  var errorMsg = "Unimplemented tag type \"".concat(part.type, "\"");
  if (part.module) {
    errorMsg += " \"".concat(part.module, "\"");
  }
  var err = new XTTemplateError(errorMsg);
  /*
   * This happens when a tag type is not implemented. It should normally not happen,
   * unless you changed Docxtemplater code or created your own module and didn't
   * implement the `render` function of your module correctly.
   */
  err.properties = {
    part: part,
    index: index,
    id: "unimplemented_tag_type"
  };
  throw err;
}
function throwMalformedXml() {
  var err = new XTInternalError("Malformed xml");
  /*
   * This happens when an xml file of the document cannot be parsed
   * correctly.
   */
  err.properties = {
    explanation: "The template contains malformed xml",
    id: "malformed_xml"
  };
  throw err;
}
function throwResolveBeforeCompile() {
  var err = new XTInternalError("You must run `.compile()` before running `.resolveData()`");
  /*
   * This happens if you're calling `resolveData()` before you run `.compile()`.
   *
   * You should always call `compile` first and then only `resolveData`
   *
   * Or you can migrate to [the constructor with two arguments](/docs/get-started-node/#usage)
   */
  err.properties = {
    id: "resolve_before_compile",
    explanation: "You must run `.compile()` before running `.resolveData()`"
  };
  throw err;
}
function throwRenderInvalidTemplate() {
  var err = new XTInternalError("You should not call .render on a document that had compilation errors");
  /*
   * This happens if you're calling `render()` on a document that had template errors
   */
  err.properties = {
    id: "render_on_invalid_template",
    explanation: "You should not call .render on a document that had compilation errors"
  };
  throw err;
}
function throwRenderTwice() {
  var err = new XTInternalError("You should not call .render twice on the same Docxtemplater instance");
  /*
   * This happens if you're calling `render()` on a document twice.
   *
   * You should always create a new Docxtemplater instance if you need to create two output documents.
   */
  err.properties = {
    id: "render_twice",
    explanation: "You should not call .render twice on the same Docxtemplater instance"
  };
  throw err;
}
function throwXmlInvalid(content, offset) {
  var err = new XTTemplateError("An XML file has invalid xml");
  /*
   * This error happens if the XML is invalid in your template file.
   *
   * This should be very rare except if you were using a tool to preprocess
   * the template (an XML error in a docx file means that the template file
   * is already corrupt).
   */
  err.properties = {
    id: "file_has_invalid_xml",
    content: content,
    offset: offset,
    explanation: "The docx contains invalid XML, it is most likely corrupt"
  };
  throw err;
}
module.exports = {
  XTError: XTError,
  XTTemplateError: XTTemplateError,
  XTInternalError: XTInternalError,
  XTScopeParserError: XTScopeParserError,
  XTAPIVersionError: XTAPIVersionError,
  // Remove this alias in v4
  RenderingError: XTRenderingError,
  XTRenderingError: XTRenderingError,
  getClosingTagNotMatchOpeningTag: getClosingTagNotMatchOpeningTag,
  getLoopPositionProducesInvalidXMLError: getLoopPositionProducesInvalidXMLError,
  getScopeCompilationError: getScopeCompilationError,
  getScopeParserExecutionError: getScopeParserExecutionError,
  getUnclosedTagException: getUnclosedTagException,
  getUnopenedTagException: getUnopenedTagException,
  getUnmatchedLoopException: getUnmatchedLoopException,
  getDuplicateCloseTagException: getDuplicateCloseTagException,
  getDuplicateOpenTagException: getDuplicateOpenTagException,
  getCorruptCharactersException: getCorruptCharactersException,
  getInvalidRawXMLValueException: getInvalidRawXMLValueException,
  getUnbalancedLoopException: getUnbalancedLoopException,
  throwApiVersionError: throwApiVersionError,
  throwFileTypeNotHandled: throwFileTypeNotHandled,
  throwFileTypeNotIdentified: throwFileTypeNotIdentified,
  throwMalformedXml: throwMalformedXml,
  throwMultiError: throwMultiError,
  throwExpandNotFound: throwExpandNotFound,
  throwRawTagShouldBeOnlyTextInParagraph: throwRawTagShouldBeOnlyTextInParagraph,
  throwUnimplementedTagType: throwUnimplementedTagType,
  throwXmlTagNotFound: throwXmlTagNotFound,
  throwXmlInvalid: throwXmlInvalid,
  throwResolveBeforeCompile: throwResolveBeforeCompile,
  throwRenderInvalidTemplate: throwRenderInvalidTemplate,
  throwRenderTwice: throwRenderTwice
};