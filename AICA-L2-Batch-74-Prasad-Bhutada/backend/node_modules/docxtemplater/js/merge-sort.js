"use strict";

function getMinFromArrays(arrays, state) {
  var minIndex = -1;
  for (var i = 0, l = arrays.length; i < l; i++) {
    if (state[i] >= arrays[i].length) {
      continue;
    }
    if (minIndex === -1 || arrays[i][state[i]].offset < arrays[minIndex][state[minIndex]].offset) {
      minIndex = i;
    }
  }
  return minIndex;
}
module.exports = function (arrays) {
  var totalLength = 0;
  for (var _i2 = 0, _arrays2 = arrays; _i2 < _arrays2.length; _i2++) {
    var array = _arrays2[_i2];
    totalLength += array.length;
  }
  arrays = arrays.filter(function (array) {
    return array.length > 0;
  });
  var resultArray = new Array(totalLength);
  var state = arrays.map(function () {
    return 0;
  });
  for (var i = 0; i < totalLength; i++) {
    var arrayIndex = getMinFromArrays(arrays, state);
    resultArray[i] = arrays[arrayIndex][state[arrayIndex]];
    state[arrayIndex]++;
  }
  return resultArray;
};