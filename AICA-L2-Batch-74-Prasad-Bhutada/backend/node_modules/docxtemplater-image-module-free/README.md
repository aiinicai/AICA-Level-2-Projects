Open Source docxtemplater image module
==========================================
This repository holds an maintained version of docxtemplater image module.

This package is open source. There is also a [paid version](https://docxtemplater.com/modules/image/) maintained by docxtemplater author.

Note this version is compatible with docxtemplater 3.x.

Installation
-------------
You first need to install docxtemplater by following its [installation guide](https://docxtemplater.readthedocs.io/en/latest/installation.html).

For Node.js install this package:
```bash
npm install docxtemplater-image-module-free
```

For the browser find builds in `build/` directory.

Alternatively, you can create your own build from the sources:
```bash
npm run compile
npm run browserify
npm run uglify
```

Usage
-----
Assuming your **docx** or **pptx** template contains only the text `{%image}`:
```javascript
//Node.js example
var ImageModule = require('open-docxtemplater-image-module');

//Below the options that will be passed to ImageModule instance
var opts = {}
opts.centered = false; //Set to true to always center images
opts.fileType = "docx"; //Or pptx

//Pass your image loader
opts.getImage = function(tagValue, tagName) {
    //tagValue is 'examples/image.png'
    //tagName is 'image'
    return fs.readFileSync(tagValue);
}

//Pass the function that return image size
opts.getSize = function(img, tagValue, tagName) {
    //img is the image returned by opts.getImage()
    //tagValue is 'examples/image.png'
    //tagName is 'image'
    //tip: you can use node module 'image-size' here
    return [150, 150];
}

var imageModule = new ImageModule(opts);

var zip = new JSZip(content);
var doc = new Docxtemplater()
    .attachModule(imageModule)
    .loadZip(zip)
    .setData({image: 'examples/image.png'})
    .render();

var buffer = doc
        .getZip()
        .generate({type:"nodebuffer"});

fs.writeFile("test.docx",buffer);
```

Some notes regarding templates:
* **docx** files: the placeholder `{%image}` must be in a dedicated paragraph.
* **pptx** files: the placeholder `{%image}` must be in a dedicated text cell.

In the browser, this shows how to get the image asynchronously :

```html
<html>
<script src="node_modules/docxtemplater/build/docxtemplater.js"></script>
<script src="node_modules/jszip/dist/jszip.js"></script>
<script src="node_modules/jszip/vendor/FileSaver.js"></script>
<script src="node_modules/jszip-utils/dist/jszip-utils.js"></script>
<script src="build/imagemodule.js"></script>
<script>
  JSZipUtils.getBinaryContent('examples/image-example.docx', function (error, content) {
    if (error) {
      console.error(error);
      return;
    }
    var opts = {}
    opts.centered = false;
    opts.getImage = function (tagValue, tagName) {
      return new Promise(function (resolve, reject) {
        JSZipUtils.getBinaryContent(tagValue, function (error, content) {
          if (error) {
            return reject(error);
          }
          return resolve(content);
        });
      });
    }
    opts.getSize = function (img, tagValue, tagName) {
      // FOR FIXED SIZE IMAGE :
      return [150, 150];

      // FOR IMAGE COMING FROM A URL (IF TAGVALUE IS AN ADRESS) :
      // To use this feature, you have to be using docxtemplater async
      // (if you are calling setData(), you are not using async).
      return new Promise(function (resolve, reject) {
        var image = new Image();
        image.src = url;
        image.onload = function () {
          resolve([image.width, image.height]);
        };
        image.onerror = function (e) {
          console.log('img, tagValue, tagName : ', img, tagValue, tagName);
          alert("An error occured while loading " + tagValue);
          reject(e);
        }
      });
    }

    var imageModule = new ImageModule(opts);

    var zip = new JSZip(content);
    var doc = new docxtemplater()
      .loadZip(zip)
      .attachModule(imageModule)
      .compile();

    doc.resolveData({
      image: 'examples/image.png'
    }).then(function () {
      console.log('ready');
      doc.render();
      var out = doc.getZip().generate({
        type: "blob",
        mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      saveAs(out, "generated.docx");
    })
  });
</script>

</html>
```

Centering images
----------------
You can center all images by setting the global switch to true `opts.centered = true`.

If you would like to choose which images should be centered one by one:
* Set the global switch to false `opts.centered = false`.
* Use `{%image}` for images that shouldn't be centered.
* Use `{%%image}` for images that you would like to see centered.

In **pptx** generated documents, images are centered vertically and horizontally relative to the parent cell.

## Async support

It is possible to get images asynchronously by returning a Promise in the getImage function and use the docxtemplater async api : http://docxtemplater.readthedocs.io/en/latest/async.html

You can also return a promise in the getSize function if you want to resolve the size asynchronously (like in the browser example above).

Here is an example in node that allows you to retrieve values from an URL and use a fixed width, and keep the aspect ratio.

```js
const fs = require("fs");
const DocxTemplater = require("docxtemplater");
const https = require("https");
const Stream = require("stream").Transform;

const ImageModule = require("./es6");
const JSZip = require("jszip");

const content = fs.readFileSync("demo_template.docx");

const data = {
  image: "https://docxtemplater.com/xt-pro.png"
};

const opts = {};
opts.getImage = function (tagValue, tagName) {
  console.log(tagValue, tagName);
  // tagValue is "https://docxtemplater.com/xt-pro-white.png" and tagName is "image"
  return new Promise(function (resolve, reject) {
    getHttpData(tagValue, function (err, data) {
      if (err) {
        return reject(err);
      }
      resolve(data);
    });
  });
};

opts.getSize = function (img, tagValue, tagName) {
  console.log(tagValue, tagName);
  // img is the value that was returned by getImage
  // This is to force the width to 600px, but keep the same aspect ration
  const sizeOf = require("image-size");
  const sizeObj = sizeOf(img);
  console.log(sizeObj);
  const forceWidth = 600;
  const ratio = forceWidth / sizeObj.width;
  return [
    forceWidth,
    // calculate height taking into account aspect ratio
    Math.round(sizeObj.height * ratio),
  ];
};

const imageModule = new ImageModule(opts);

const zip = new JSZip(content);
const doc = new DocxTemplater()
  .loadZip(zip)
  .attachModule(imageModule)
  .compile();

doc
  .resolveData(data)
  .then(function () {
    console.log("data resolved");
    doc.render();
    const buffer = doc
      .getZip()
      .generate({
        type: "nodebuffer",
        compression: "DEFLATE"
      });

    fs.writeFileSync("test.docx", buffer);
    console.log("rendered");
  })
  .catch(function (error) {
    console.log("An error occured", error);
  });

function getHttpData(url, callback) {
  https
    .request(url, function (response) {
      if (response.statusCode !== 200) {
        return callback(
          new Error(
            `Request to ${url} failed, status code: ${response.statusCode}`
          )
        );
      }

      const data = new Stream();
      response.on("data", function (chunk) {
        data.push(chunk);
      });
      response.on("end", function () {
        callback(null, data.read());
      });
      response.on("error", function (e) {
        callback(e);
      });
    })
    .end();
}
```

## Size and path based on placeholder

You can have customizable image loader using the template's placeholder name.

```
opts.getImage = function (tagValue, tagName) {
    if(tagName === 'logo')
        return fs.readFileSync(__dirname + '/logos/' + tagValue);

    return fs.readFileSync(__dirname + '/images/' + tagValue);
};
```

The same thing can be used to customize image size.

```
opts.getSize = function (img, tagValue, tagName) {
    if(tagName === 'logo')
        return [100, 100];

    return [300, 300];
};
```

## Base64 include

You can use base64 images with the following code:

```js
function base64DataURLToArrayBuffer(dataURL) {
  const base64Regex = /^data:image\/(png|jpg|svg|svg\+xml);base64,/;
  if (!base64Regex.test(dataURL)) {
    return false;
  }
  const stringBase64 = dataURL.replace(base64Regex, "");
  let binaryString;
  if (typeof window !== "undefined") {
    binaryString = window.atob(stringBase64);
  } else {
    binaryString = new Buffer(stringBase64, "base64").toString("binary");
  }
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    const ascii = binaryString.charCodeAt(i);
    bytes[i] = ascii;
  }
  return bytes.buffer;
}
const imageOpts = {
  getImage(tag) {
    return base64DataURLToArrayBuffer(tag);
  },
  getSize() {
    return [100, 100];
  },
};
doc.attachModule(new ImageModule(imageOpts));
```

 