(() => {
  // Clear warmup state created earlier now that the
  // app has successfully started.
  try {
    sessionStorage.removeItem('warmup_start_time');
    sessionStorage.removeItem('warmup_last_reload_time');
    sessionStorage.removeItem('warmup_failed_sent');
  } catch (e) {
    // Ignore storage errors in restricted iframe environments.
  }

  if (window.self === window.top) {
    const params = new URLSearchParams(window.location.search);
    if (params.has('__auto_close')) {
      window.close();
    }
    // Do not run the shim in the main window, only in iframes.
    return;
  }

  if (typeof HTMLCanvasElement !== 'undefined') {
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(
      type,
      attributes,
      ...args
    ) {
      if (
        type === 'webgl' ||
        type === 'webgl2' ||
        type === 'experimental-webgl'
      ) {
        attributes = {
          ...attributes,
          preserveDrawingBuffer: true,
        };
        return originalGetContext.call(this, type, attributes, ...args);
      }
      return originalGetContext.apply(this, arguments);
    };
  }

  window.API_KEY = 'GEMINI_API_KEY';
  window.GEMINI_API_KEY = 'GEMINI_API_KEY';
  window.process = window.process || {};
  window.process.env = window.process.env || {};
  window.process.env.API_KEY = window.API_KEY;
  window.process.env.GEMINI_API_KEY = window.GEMINI_API_KEY;

  const bootstrapChannel = new Promise((resolve) => {
    window.addEventListener('message', (event) => {
      try {
        const url = new URL(event.origin);
        if (!url.hostname.endsWith('.google.com')) {
          return;
        }
      } catch (e) {
        return;
      }

      if (event.data.type === 'bootstrap') {
        resolve({
          port: event.ports[0],
          urlPatterns:
              event.data.urlPatterns.map((pattern) => new RegExp(pattern)),
        });
      }
    });
  });

  window.aistudio = window.aistudio || {
    handleFullscreenEsc: true,
    getHostUrl: async function() {
      const hostPort = (await bootstrapChannel).port;
      return new Promise((resolve) => {
        const channel = new MessageChannel();
        hostPort.postMessage(
            {type: 'get_host_url'},
            [channel.port2]);
        const port = channel.port1;
        port.onmessage = (message) => {
          resolve(message.data.url);
        };
      });
    },
    hasSelectedApiKey: async function() {
      const hostPort = (await bootstrapChannel).port;
      return new Promise((resolve) => {
        const channel = new MessageChannel();
        hostPort.postMessage(
            {type: 'has_selected_api_key'},
            [channel.port2]);
        const port = channel.port1;
        port.onmessage = (message) => {
          resolve(message.data);
        };
      });
    },
    openSelectKey: async function() {
      const hostPort = (await bootstrapChannel).port;
      const channel = new MessageChannel();
      hostPort.postMessage(
          {type: 'open_select_key'},
          [channel.port2]);
    },
    getModelQuota: async function(model) {
      const hostPort = (await bootstrapChannel).port;
      return new Promise((resolve) => {
        const channel = new MessageChannel();
        hostPort.postMessage(
            {type: 'get_model_quota', model},
            [channel.port2]);
        const port = channel.port1;
        port.onmessage = (message) => {
          resolve(message.data.modelQuota);
        };
      });
    },
  };

  const nativeFetch = window.fetch;

  /**
   * @param {string | URL | Request} resource The resource of the fetch request.
   * @param {RequestInit} options The options of the fetch request.
   * @return {Promise!} The promise of the fetch request.
   */
  async function fetch(resource, options) {
    const config = await bootstrapChannel;

    const request = resource instanceof Request ?
      resource.clone() :
      new Request(resource, options);

    if (!config.urlPatterns.some((pattern) => request.url.match(pattern))) {
      return nativeFetch(resource, options);
    }
    const hostPort = config.port;

    const channel = new MessageChannel();
    const port = channel.port1;
    let bodyBytes;
    const transfer = [channel.port2];
    const parts = [];
    const buffer = await request.arrayBuffer();
    if (buffer.byteLength) {
      bodyBytes = buffer;
      transfer.push(bodyBytes);
    }
    hostPort.postMessage(
        {
          type: 'fetch',
          url: request.url,
          method: request.method,
          headers: [...request.headers.entries()],
          body: bodyBytes,
        },
        transfer);

    let streamController;
    const body = new ReadableStream({
      start(controller) {
        streamController = controller;
      },
    });
    let resolveReceive;
    const receivePromise = new Promise((resolve) => {
      resolveReceive = resolve;
    });
    port.onmessage = (message) => {
      switch (message.data.type) {
        case 'response':
          resolveReceive(new Response(body, {
            status: message.data.status,
            statusText: message.data.statusText,
            headers: new Headers(message.data.headers),
          }));
          break;
        case 'body':
          streamController.enqueue(message.data.data);
          break;
        case 'body_done':
          streamController.close();
          break;
      }
    };
    return receivePromise;
  }

  Object.defineProperty(window, 'fetch', {
    get: function() {
      return fetch;
    },
  });

  // See details in: https://github.com/angular/angular/issues/63064.
  function patchHistoryStateFunctionForAngular(originalFn, baseHref) {
    return (state, unused, url) => {
      if (typeof url === 'string' && !url.startsWith('blob:')) {
        url = baseHref + url;
      }
      return originalFn.apply(window.history, [state, unused, url]);
    };
  }

  const originalWebSocket = window.WebSocket;
  class ProxiedWebSocket extends EventTarget {
    /**
     * @param {string} url The url of the websocket.
     * @param {Object!} protocols The protocols of the websocket.
     */
    constructor(url, protocols) {
      super();
      this.url = url;
      this.protocols = protocols;

      this.open();
    }

    /** Opens the websocket. */
    async open() {
      const hostPort = (await bootstrapChannel).port;
      const channel = new MessageChannel();
      hostPort.postMessage(
          {type: 'websocket_open', url: this.url, protocols: this.protocols},
          [channel.port2]);
      this.port = channel.port1;
      this.port.onmessage = (message) => {
        if (message.data.type === 'close') {
          const event = new CloseEvent('close', {
            code: message.data.code,
            reason: message.data.reason,
            wasClean: message.data.wasClean,
          });
          if (this.onclose) {
            this.onclose(event);
          }
          this.dispatchEvent(event);
          return;
        } else if (message.data.type === 'open') {
          const event = new Event('open');
          if (this.onopen) {
            this.onopen(event);
          }
          this.dispatchEvent(event);
          return;
        } else if (message.data.type === 'message') {
          let data = message.data.data;
          if (message.data.messageType === 'text' || message.data.messageType === 'message') {
            data = new TextDecoder().decode(data);
          }
          const event = new MessageEvent('message', {
            data,
            type: message.data.messageType,
          });
          if (this.onmessage) {
            this.onmessage(event);
          }
          this.dispatchEvent(event);
          return;
        } else if (message.data.type === 'error') {
          const event = new ErrorEvent('error', {
            message: message.data.message,
          });
          if (this.onerror) {
            this.onerror(event);
          }
          this.dispatchEvent(event);
          return;
        }
        console.error('received unknown message in frame', event.data);
      };
    }
    /**
     * @param {string|ArrayBuffer!} data The data to send.
     */
    send(data) {
      if (typeof data === 'string') {
        this.port.postMessage({type: 'send', data});
      } else {
        this.port.postMessage({type: 'send', data}, [data.buffer]);
      }
    }

    /**
     * @param {number} code The code of the close event.
     * @param {string} reason The reason of the close event.
     */
    close(code, reason) {
      this.port.postMessage({type: 'close', code, reason});
    }
  }

  /**
   * @param {string} url The url of the websocket.
   * @param {Object!} protocols The protocols of the websocket.
   * @return {WebSocket!} The websocket.
   */
  function createWebSocket(url, protocols) {
    // This should come from the bootstrap channel, but we want this to
    // work for the synchronous constructor here.
    if (url.startsWith('wss://generativelanguage.googleapis.com/')) {
      return Reflect.construct(ProxiedWebSocket, [url, protocols]);
    }
    return Reflect.construct(originalWebSocket, [url, protocols]);
  }

  Object.defineProperty(window, 'WebSocket', {
    get: function() {
      const fn = createWebSocket;
      Object.keys(originalWebSocket).forEach((key) => {
        Object.defineProperty(fn, key, {
          value: originalWebSocket[key],
        });
      });
      return fn;
    },
  });

  async function instrumentErrorReporting() {
    const errors = [];
    let hostPort;

    function reportError(message) {
      if (!hostPort) {
        errors.push(message);
      } else {
        hostPort.postMessage({type: 'error', message: message}, message);
      }
    }

    // JSON.stringify throws on circular references and BigInt values, which can
    // happen in applet state objects. Retry with a replacer that breaks cycles
    // and stringifies BigInts so the remaining fields are still reported.
    function stringifyCycleSafe(a) {
      const seen = new WeakSet();
      return JSON.parse(JSON.stringify(a, (key, value) => {
        if (typeof value === 'bigint') {
          return String(value);
        }
        if (value !== null && typeof value === 'object') {
          if (seen.has(value)) {
            return '[Circular]';
          }
          seen.add(value);
        }
        return value;
      }));
    }

    function serialize(args) {
      return args.map((a) => {
        if (a instanceof Error || a instanceof ErrorEvent) {
          const errObj = a instanceof ErrorEvent ? a.error : a;
          return errObj?.stack || errObj?.message || a.message;
        }
        if(a instanceof CloseEvent) {
          return {code: a.code, reason: a.reason, wasClean: a.wasClean};
        }
        if( a instanceof Map) {
          return JSON.parse(JSON.stringify([...a.entries()]));
        }
        if( a instanceof Set) {
          return JSON.parse(JSON.stringify([...a.values()]));
        }
        if (a instanceof Object) {
          try {
            return JSON.parse(JSON.stringify(a));
          } catch (e) {
            try {
              return stringifyCycleSafe(a);
            } catch (e2) {
              // Last resort for values that cannot be serialized at all, e.g.
              // objects with getters that throw.
              return String(a);
            }
          }
        }
        return a;
      });
    }

    const originalConsole = window.console;
    const originalConsoleLog = window.console.log;
    const originalConsoleError = window.console.error;
    const originalConsoleWarn = window.console.warn;
    const originalConsoleDebug = window.console.debug;
    window.console = {
      ...originalConsole,
      log: (message, ...args) => {
        originalConsoleLog.apply(window.console, [message, ...args]);
        const combined = serialize([message, ...args]);
        reportError({type: 'console_log', message: combined });
      },
      debug: (message, ...args) => {
        originalConsoleDebug.apply(window.console, [message, ...args]);
        const combined = serialize([message, ...args]);
        reportError({type: 'console_debug', message: combined });
      },
      error: (message, ...args) => {
        originalConsoleError.apply(window.console, [message, ...args]);
        const combined = serialize([message, ...args]);
        const errorArg = [message, ...args].find(
            (a) => a instanceof Error || a instanceof ErrorEvent,
        );
        const payload = {type: 'console_error', message: combined};
        if (errorArg) {
          const errorObj =
              errorArg instanceof ErrorEvent ? errorArg.error : errorArg;
          if (errorObj) {
            if (errorObj.name) {
              payload.errorName = errorObj.name;
            }
            if (errorObj.code !== undefined && errorObj.code !== null) {
              payload.errorCode = errorObj.code;
            }
            if (errorObj.stack) {
              payload.stack = errorObj.stack;
            }
          }
        }
        reportError(payload);
      },
      warn: (message, ...args) => {
        originalConsoleWarn.apply(window.console, [message, ...args]);
        const combined = serialize([message, ...args]);
        reportError({type: 'console_warn', message: combined });
      },
    };

    window.onerror = (message, source, lineno, colno, error) => {
      let stack = error?.stack;
      if (!stack && (source || lineno)) {
        stack = `${message}\n    at ${source || 'unknown'}:${lineno || '?'}:${colno || '?'}`;
      }
      reportError({
        type: 'error',
        message: serialize([message]),
        source,
        lineno,
        colno,
        errorName: error?.name,
        errorCode: error?.code,
        stack,
      });
    };

    window.onunhandledrejection = (event) => {
      const reason = event.reason;
      const stack = typeof reason?.stack === 'string' ? reason.stack : undefined;
      reportError({
        type: 'unhandledrejection',
        message: serialize([reason]),
        errorName: reason?.name,
        errorCode: reason?.code,
        stack,
      });
    };

    window.alert = (message) => {
      reportError({type: 'alert', message: serialize([message]) });
    };

    hostPort = (await bootstrapChannel).port;
    for(const error of errors) {
      hostPort.postMessage({type: 'error', message: error});
    }
  }

  const availableFiles = new Set(window.APPLET_FILES || []);

  instrumentErrorReporting();

  const notifyLocationChange = async () => {
    const hostPort = (await bootstrapChannel).port;
    hostPort.postMessage({type: 'locationchange', href: location.href});
  };

  // Send initial state on load.
  notifyLocationChange();

  const originalPushState = history.pushState;
  history.pushState = (...args) => {
    originalPushState.apply(history, args);
    notifyLocationChange();
  };

  const originalReplaceState = history.replaceState;
  history.replaceState = (...args) => {
    originalReplaceState.apply(history, args);
    notifyLocationChange();
  };
  window.addEventListener('popstate', (e) => {
    notifyLocationChange();
  });

  window.addEventListener('hashchange', async (e) =>{
    const config = await bootstrapChannel;
    const hostPort = config.port;
    hostPort.postMessage({type: 'hashchange', hash: window.location.hash});
    hostPort.postMessage({
      type: 'locationchange',
      href: location.href,
    });
  });

  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/html2canvas-pro@2.0.4';
  script.onload = () => {
    window.addEventListener('message', async (event) => {
      if (event.data?.type === 'capture-screenshot') {
        try {
          const canvas = await html2canvas(document.documentElement, {
            logging: false,
            useCORS: true,
            backgroundColor: null,
            scale: 1,
          });
          const hostPort = (await bootstrapChannel).port;
          hostPort.postMessage(
            {
              type: 'screenshot-result',
              dataUrl: canvas.toDataURL('image/png'),
              requestId: event.data.requestId,
              scrollX: document.body.scrollLeft,
              scrollY: document.body.scrollTop,
            },
          );
        } catch (e) {
          const hostPort = (await bootstrapChannel).port;
          hostPort.postMessage(
            {
              type: 'screenshot-error',
              error: e.message,
              requestId: event.data.requestId,
            });
        }
      }
    });
  };
  document.head.appendChild(script);

  const MAX_ANCESTOR_LEVEL = 3;
  const MAX_DESCENDANT_LEVEL = 3;

  function getElementSelector(el) {
    if (!el || el.nodeType !== 1) {
      return '';
    }
    const parts = [];
    while(el && el.nodeType === 1 && el.tagName.toLowerCase() !== 'body') {
      let part = el.tagName.toLowerCase();
      if (el.id) {
        part += '#' + CSS.escape(el.id);
      }

      const parent = el.parentElement;
      if (parent) {
        let nth = 1;
        let prev = el.previousElementSibling;
        while(prev) {
          if (prev.tagName === el.tagName) {
            nth++;
          }
          prev = prev.previousElementSibling;
        }
        part += ':nth-of-type(' + nth + ')';
      }

      parts.unshift(part);
      el = el.parentElement;
    }
    return parts.join(' > ');
  }

  function getDomTreeAsString(element, depth, maxDepth) {
    if (!element || element.nodeType !== 1 || depth > maxDepth) {
      return '';
    }
    const tagName = element.tagName.toLowerCase();
    let attrs = [];
    if (element.id) {
      attrs.push('id="' + element.id + '"');
    }
    if (element.classList.length > 0) {
      attrs.push('class="' + element.classList.value + '"');
    }
    const attrString = attrs.length > 0 ? ' ' + attrs.join(' ') : '';

    let content = '';
    for (const node of element.childNodes) {
      if (node.nodeType === 1) { // Element node
        content += getDomTreeAsString(node, depth + 1, maxDepth);
      } else if (node.nodeType === 3) { // Text node
        content += node.textContent;
      }
    }

    return '<' + tagName + attrString + '>' + content + '</' + tagName + '>';
  }

  let activeElementCss = {};

  function getElementInfo(element, isUpdate = false) {
    const selector = getElementSelector(element);
    let levelsUp = 0;
    let root = element;
    while(levelsUp < MAX_ANCESTOR_LEVEL && root.parentElement && root.parentElement.tagName.toLowerCase() !== 'html') {
      root = root.parentElement;
      levelsUp++;
    }
    const domString = getDomTreeAsString(root, 0, levelsUp + MAX_DESCENDANT_LEVEL);

    if (!isUpdate) {
      const styles = window.getComputedStyle(element);
      activeElementCss = {};
      for (let i = 0; i < styles.length; i++) {
        const key = styles[i];
        activeElementCss[key] = styles.getPropertyValue(key);
      }
    }
    let src = element.src || '';
    const imgChild = element.querySelector(':scope > img');
    const hasImgChild = !!imgChild;
    if (!src && imgChild) {
      src = imgChild.src || '';
    }
    // Compute a data URL for cross-origin image access. The host page cannot
    // fetch image URLs from the sandboxed iframe origin due to CORS. By
    // converting via canvas here (where we have same-origin access), the host
    // can use srcDataUrl directly for image regeneration.
    let srcDataUrl = '';
    if (src && !src.startsWith('data:')) {
      try {
        const imgEl = element.tagName.toLowerCase() === 'img' ? element : imgChild;
        if (imgEl && imgEl.complete && imgEl.naturalWidth > 0) {
          const canvas = document.createElement('canvas');
          canvas.width = imgEl.naturalWidth;
          canvas.height = imgEl.naturalHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(imgEl, 0, 0);
          srcDataUrl = canvas.toDataURL('image/png');
        }
      } catch (e) {
        // If canvas conversion fails (e.g. tainted canvas), leave empty.
      }
    } else if (src.startsWith('data:')) {
      srcDataUrl = src;
    }
    const rect = element.getBoundingClientRect();
    const tagName = element.tagName.toLowerCase();
    return { selector, domString, css: activeElementCss, src, srcDataUrl, hasImgChild, x: rect.left, y: rect.top, width: rect.width, height: rect.height, tagHeight: focusTag ? focusTag.offsetHeight : 0, alt: element.alt || '', tagName };
  }

  function loadGoogleFont(fontFamilyValue) {
    const family = fontFamilyValue.split(',')[0].trim().replace(/['"]/g, '');
    const ignoredValues = [
      'Arial',
      'Courier New',
      'Georgia',
      'Times New Roman',
      'Verdana',

      'cursive',
      'emoji',
      'fangsong',
      'fantasy',
      'math',
      'monospace',
      'sans-serif',
      'serif',
      'system-ui',
      'ui-monospace',
      'ui-rounded',
      'ui-sans-serif',
      'ui-serif',
    ];
    if (!family || ignoredValues.includes(family)) {
      return;
    }

    const id = `google-font-${family.replace(/\s+/g, '-').toLowerCase()}`;
    if (document.getElementById(id)) {
      return;
    }

    const link = document.createElement('link');
    link.id = id;
    link.rel = 'stylesheet';
    link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:wght@400;700&display=swap`;
    document.head.appendChild(link);
  }

  const style = document.createElement('style');
  style.textContent =
    '.aistudio-hover-highlight { box-shadow: inset 0 0 0 0.5px white, inset 0 0 0 1.5px rgba(128,128,128,0.6) !important; }' +
    '.aistudio-active-highlight { outline: 2px solid #87a9ff !important; outline-offset: -2px !important; box-shadow: 0 0 0 0.5px rgba(0,0,0,0.3), inset 0 0 0 0.5px rgba(0,0,0,0.3) !important; }' +
    '.aistudio-generating-blur { filter: blur(5px) grayscale(100%) brightness(28%) !important; transition: filter 0.3s ease; }' +
    '#aistudio-focus-mode-tag { position: absolute; display: none; align-items: center; gap: 4px; background: #87a9ff; border-radius: 12px; z-index: 10000; padding: 8px; color: #32302c; font-family: Inter, sans-serif; font-size: 14px; font-style: normal; font-weight: 500; line-height: 21px; pointer-events: none; }' +
    '#aistudio-hover-mode-tag { position: absolute; display: none; align-items: center; gap: 4px; background: rgba(128,128,128,0.6); border-radius: 12px; z-index: 10000; padding: 8px; color: white; font-family: Inter, sans-serif; font-size: 14px; font-style: normal; font-weight: 500; line-height: 21px; pointer-events: none; }' +
    '.aistudio-img-icon { display: none; vertical-align: middle; pointer-events: auto; cursor: pointer; }' +
    '.aistudio-img-icon.visible { display: inline-flex; }' +
    '#aistudio-focus-mode-tag .aistudio-img-icon { position: relative; width: 26px; height: 26px; background: #32302c; border-radius: 6px; margin: -4px -4px -4px 0; }' +
    '#aistudio-focus-mode-tag .aistudio-img-icon::before { content: ""; position: absolute; top: 4px; left: 4px; width: 18px; height: 18px; background-color: white; -webkit-mask-image: url("https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/edit_fix_auto/default/24px.svg"); -webkit-mask-size: contain; -webkit-mask-repeat: no-repeat; mask-image: url("https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/edit_fix_auto/default/24px.svg"); mask-size: contain; mask-repeat: no-repeat; }' +
    '#aistudio-hover-mode-tag .aistudio-img-icon { position: relative; width: 18px; height: 18px; margin-left: 4px; }' +
    '#aistudio-hover-mode-tag .aistudio-img-icon::before { content: ""; position: absolute; top: 0; left: 0; width: 18px; height: 18px; background-color: white; -webkit-mask-image: url("https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/edit_fix_auto/default/24px.svg"); -webkit-mask-size: contain; -webkit-mask-repeat: no-repeat; mask-image: url("https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/edit_fix_auto/default/24px.svg"); mask-size: contain; mask-repeat: no-repeat; }' +
    '#aistudio-focus-mode-tag .aistudio-img-icon:hover, #aistudio-hover-mode-tag .aistudio-img-icon:hover { background: #424242 !important; }' +
    '#aistudio-focus-mode-tag .aistudio-img-icon:active, #aistudio-hover-mode-tag .aistudio-img-icon:active { background: #393f51 !important; }';
  document.head.appendChild(style);

  let hoveredElement = null;
  let activeElement = null;
  let focusTag = null;
  let hoverTag = null;
  let resizeObserver = null;
  let iframeLoaded = false;
  let designModeEnabled = false;
  let designModeStyle = null;
  let designModeOverlay = null;
  let generatingElement = null;

  function createImgIcon() {
    const icon = document.createElement('span');
    icon.className = 'aistudio-img-icon';
    icon.setAttribute('aria-label', 'Regenerate image');
    icon.setAttribute('title', 'Regenerate image');
    icon.setAttribute('role', 'button');
    return icon;
  }

  function updateTagContent(tag, element) {
    let label = tag.querySelector('.aistudio-tag-label');
    if (label) {
      label.textContent = getTagLabel(element);
    } else {
      label = document.createElement('span');
      label.className = 'aistudio-tag-label';
      label.textContent = getTagLabel(element);
      tag.insertBefore(label, tag.firstChild);
    }
    const imgIcon = tag.querySelector('.aistudio-img-icon');
    if (imgIcon) {
      imgIcon.classList.toggle('visible',
          (element.tagName.toLowerCase() === 'img' || element.querySelector(':scope > img')));
    }
  }

  function getTagLabel(element) {
    const tagName = element.tagName.toLowerCase()
    if (tagName == 'img') {
      return 'Image';
    }
    return tagName;
  }

  function createModeTag(id, isHoverMode) {
    const tag = document.createElement('div');
    tag.id = id;
    const icon = createImgIcon();
    icon.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const element = isHoverMode ? hoveredElement : activeElement;
      if (element) {
        if (isHoverMode && element !== activeElement) {
          setActiveElement(element);
        }
        const info = getElementInfo(element);
        window.parent.postMessage({
          type: 'open-image-regenerator',
          element: info,
        }, '*');
      }
    });
    tag.appendChild(icon);
    document.body.appendChild(tag);
    return tag;
  }

  function ensureFocusTag() {
    if (!focusTag) {
      focusTag = createModeTag('aistudio-focus-mode-tag', false);
    }
  }

  function cleanupActiveElement() {
    if (!activeElement) return;
    activeElement.classList.remove('aistudio-active-highlight');
    activeElement.removeAttribute('data-aistudio-tag-name');
    if (resizeObserver) {
      resizeObserver.unobserve(activeElement);
    }
    window.removeEventListener('resize', positionFocusTag);
    window.removeEventListener('scroll', onScroll, true);
  }

  function positionTag(tag, element) {
    if (!element || !tag) return;
    tag.style.display = 'inline-flex';
    const height = tag.offsetHeight;
    const rect = element.getBoundingClientRect();
    tag.style.top = (rect.top + window.scrollY - height - 3) + 'px';
    tag.style.left = (rect.left + window.scrollX) + 'px';
  }

  function positionFocusTag() {
    requestAnimationFrame(() => {
      positionTag(focusTag, activeElement);
    });
  }

  let scrollScheduled = false;

  function onScroll() {
    positionFocusTag();
    if ((activeElement || generatingElement) && !scrollScheduled) {
      scrollScheduled = true;
      requestAnimationFrame(() => {
        if (activeElement) {
          const info = getElementInfo(activeElement, true);
          window.parent.postMessage({
            type: 'element-selected',
            element: info,
          }, '*');
        }
        if (generatingElement && generatingElement !== activeElement) {
          const info = getElementInfo(generatingElement, true);
          window.parent.postMessage({
            type: 'generating-element-moved',
            element: info,
          }, '*');
        }
        scrollScheduled = false;
      });
    }
  }

  function positionHoverTag() {
    if (!hoveredElement || !hoverTag || hoveredElement === activeElement) {
      if (hoverTag) hoverTag.style.display = 'none';
      return;
    }
    requestAnimationFrame(() => {
      positionTag(hoverTag, hoveredElement);
    });
  }

  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      positionFocusTag();
    });
  }

  function ensureHoverTag() {
    if (!hoverTag) {
      hoverTag = createModeTag('aistudio-hover-mode-tag', true);
    }
  }

  function setHoveredElement(element) {
    if (!designModeEnabled || !iframeLoaded) return;

    ensureHoverTag();

    if (hoveredElement && hoveredElement !== activeElement) {
      hoveredElement.classList.remove('aistudio-hover-highlight');
    }
    hoverTag.style.display = 'none';

    hoveredElement = element;

    if (hoveredElement && hoveredElement !== activeElement) {
      hoveredElement.classList.add('aistudio-hover-highlight');
      updateTagContent(hoverTag, hoveredElement);
      positionHoverTag();
    }
  }

  async function setActiveElement(element, notifyHost = true) {
    if (!designModeEnabled || !iframeLoaded) return;

    if (activeElement === element) {
      return;
    }

    ensureFocusTag();
    cleanupActiveElement();
    focusTag.style.display = 'none';
    if (hoverTag) {
      hoverTag.style.display = 'none';
    }

    if (element) {
      element.classList.remove('aistudio-hover-highlight');
    }

    activeElement = element;

    if (activeElement) {
      activeElement.setAttribute('data-aistudio-tag-name', activeElement.tagName);
      activeElement.classList.add('aistudio-active-highlight');
      updateTagContent(focusTag, activeElement);

      positionFocusTag();
      if (resizeObserver) {
        resizeObserver.observe(activeElement);
      }
      window.addEventListener('resize', positionFocusTag);
      window.addEventListener('scroll', onScroll, true);

      if (notifyHost) {
        const info = getElementInfo(activeElement);
        window.parent.postMessage({
          type: 'element-selected',
          element: info,
        }, '*');
      }
    }
  }

  function getElementAtPoint(x, y) {
    const elements = document.elementsFromPoint(x, y);
    let fallback = null;
    let imgAtPoint = null;
    for (const el of elements) {
      if (el.id === 'aistudio-focus-mode-tag' ||
          el.id === 'aistudio-hover-mode-tag' ||
          el.id === 'aistudio-design-mode-overlay') {
        continue;
      }
      if (!imgAtPoint && el.tagName.toLowerCase() === 'img') {
        imgAtPoint = el;
      }
      if (!fallback) {
        fallback = el;
      }
    }
    if (imgAtPoint && fallback && fallback !== imgAtPoint &&
        !fallback.textContent.trim()) {
      return imgAtPoint;
    }
    return fallback;
  }

  function isPointInRect(x, y, rect) {
    return x >= rect.left && x <= rect.right &&
           y >= rect.top && y <= rect.bottom;
  }

  function getIconTargetElement(e) {
    const focusImgIcon = focusTag?.querySelector('.aistudio-img-icon.visible');
    const hoverImgIcon = hoverTag?.querySelector('.aistudio-img-icon.visible');

    if (focusImgIcon && isPointInRect(e.clientX, e.clientY, focusImgIcon.getBoundingClientRect())) {
      return activeElement;
    }
    if (hoverImgIcon && isPointInRect(e.clientX, e.clientY, hoverImgIcon.getBoundingClientRect())) {
      return hoveredElement;
    }

    return null;
  }

  function onMouseMove(e) {
    if (!designModeEnabled) return;
    const target = getIconTargetElement(e);
    if (target) {
      if (target !== hoveredElement) {
        setHoveredElement(null);
      }
      return;
    }

    if (hoverTag && hoverTag.style.display !== 'none') {
      const rect = hoverTag.getBoundingClientRect();
      // Add 5px tolerance at the bottom to bridge the gap to the element
      if (e.clientX >= rect.left && e.clientX <= rect.right &&
          e.clientY >= rect.top && e.clientY <= rect.bottom + 5) {
        return;
      }
    }

    const element = getElementAtPoint(e.clientX, e.clientY);
    setHoveredElement(element);
  }

  function onClick(e) {
    if (!designModeEnabled) return;
    e.preventDefault();
    e.stopPropagation();

    const element = getElementAtPoint(e.clientX, e.clientY);
    if (element && element !== document.body) {
      setActiveElement(element);
    }
  }

  function onKeyDown(e) {
    if (!designModeEnabled) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      const element = document.activeElement;
      if (element && element !== document.body) {
        setActiveElement(element);
      }
    }
  }

  function enableDesignMode() {
    if (designModeEnabled) return;
    designModeEnabled = true;
    designModeStyle = document.createElement('style');
    designModeStyle.textContent =
      'button:disabled, input:disabled, select:disabled, textarea:disabled, ' +
      '[disabled], [aria-disabled="true"] { pointer-events: auto !important; }';
    document.head.appendChild(designModeStyle);
    designModeOverlay = document.createElement('div');
    designModeOverlay.id = 'aistudio-design-mode-overlay';
    designModeOverlay.style.cssText =
      'position: fixed; top: 0; left: 0; width: 100%; height: 100%; ' +
      'z-index: 9999; cursor: default; background: transparent;';
    designModeOverlay.addEventListener('mousemove', onMouseMove);
    designModeOverlay.addEventListener('mousedown', onClick);
    designModeOverlay.addEventListener('keydown', onKeyDown);
    document.body.appendChild(designModeOverlay);
  }

  function disableDesignMode() {
    if (!designModeEnabled) return;
    if (designModeOverlay) {
      designModeOverlay.removeEventListener('mousemove', onMouseMove);
      designModeOverlay.removeEventListener('mousedown', onClick);
      designModeOverlay.removeEventListener('keydown', onKeyDown);
      designModeOverlay.remove();
      designModeOverlay = null;
    }
    setHoveredElement(null);
    clearActiveElement();
    if (designModeStyle) {
      designModeStyle.remove();
      designModeStyle = null;
    }
    designModeEnabled = false;
  }

  function clearActiveElement() {
    ensureFocusTag();
    cleanupActiveElement();
    focusTag.style.display = 'none';
    activeElement = null;
  }

  function getPageHtml() {
    const clonedDoc = document.documentElement.cloneNode(true);
    let cssText = '';
    for (const sheet of document.styleSheets) {
      try {
        const rules = sheet.cssRules || sheet.rules;
        for (const rule of rules) {
          cssText += rule.cssText + '\n';
        }
      } catch (e) {
        console.warn("CORS issue reading stylesheet: ", sheet.href);
      }
    }
    const styleTag = document.createElement('style');
    styleTag.textContent = cssText;
    const clonedHead = clonedDoc.querySelector('head');
    if (clonedHead) {
      clonedHead.querySelectorAll('link[rel="stylesheet"]').forEach(el => el.remove());
      clonedHead.appendChild(styleTag);
    }
    clonedDoc.querySelectorAll('script').forEach(el => el.remove());
    return '<!DOCTYPE html>\n' + clonedDoc.outerHTML;
  }

  window.addEventListener('load', () => {
    iframeLoaded = true;
  });

  window.addEventListener('message', async (event) => {
    switch (event.data?.type) {
      case 'set-design-mode':
        if (event.data.enabled) {
          enableDesignMode();
        } else {
          disableDesignMode();
        }
        break;

      case 'highlight-element-by-selector':
        try {
          const selector = event.data.selector;
          if (selector) {
            const element = document.querySelector(selector);
            setActiveElement(element, /* notifyHost= */ false);
          } else {
            setActiveElement(null, /* notifyHost= */ false);
          }
        } catch (e) {
          setActiveElement(null, /* notifyHost= */ false);
        }
        break;

      case 'toggle-generating-state':
        try {
          const selector = event.data.selector;
          if (selector) {
            const element = document.querySelector(selector);
            if (element) {
              console.log('Toggling generating state for ', selector, event.data.enabled);
              if (event.data.enabled) {
                element.classList.add('aistudio-generating-blur');
                generatingElement = element;
              } else {
                element.style.transition = 'filter 0.3s ease';
                element.classList.remove('aistudio-generating-blur');
                generatingElement = null;
                setTimeout(() => {
                  element.style.transition = '';
                }, 300);
              }
            }
          }
        } catch (e) {}
        break;

      case 'change-element-style':
        try {
          const selector = event.data.selector;
          if (selector) {
            const element = document.querySelector(selector);
            if (element) {
              element.style.setProperty(
                event.data.property,
                event.data.value,
                'important',
              );
              if (event.data.property === 'font-family') {
                loadGoogleFont(event.data.value);
              }
              positionFocusTag();
            }
          }
        } catch (e) {}
        break;

      case 'image-generated':
        try {
          const selector = event.data.selector;
          const dataUrl = event.data.dataUrl;
          if (selector && dataUrl) {
            const element = document.querySelector(selector);
            if (element) {
              const updateImg = (img) => {
                const originalTransition = img.style.transition;
                const originalOpacity = img.style.opacity;
                img.style.transition = 'opacity 0.15s ease';
                img.style.opacity = '0.3';
                setTimeout(() => {
                  img.srcset = '';
                  img.src = dataUrl;
                  setTimeout(() => {
                    img.style.opacity = originalOpacity || '1';
                    setTimeout(() => {
                      img.style.transition = originalTransition;
                    }, 150);
                  }, 50);
                }, 150);
              };

              if (element.tagName.toLowerCase() === 'img') {
                updateImg(element);
              } else {
                const imgChild = element.querySelector(':scope > img');
                if (imgChild) {
                  updateImg(imgChild);
                }
              }
            }
          }
        } catch (e) {}
        break;

      case 'get-page-html':
        try {
          const finalHTML = getPageHtml();

          const hostPort = (await bootstrapChannel).port;
          hostPort.postMessage({
            type: 'page-html-result',
            html: finalHTML,
            requestId: event.data.requestId,
            width: window.innerWidth
          });
        } catch (e) {
          const hostPort = (await bootstrapChannel).port;
          hostPort.postMessage({
            type: 'page-html-error',
            error: e.message,
            requestId: event.data.requestId
          });
        }
        break;

      case 'apply-theme':
        try {
          // Remove all custom theme style tags first.
          document.querySelectorAll('style.aistudio-temp-theme').forEach(el => el.remove());

          const theme = event.data.theme;
          if (theme) {
            let styleTag = document.getElementById('dynamic-theme');
            if (!styleTag) {
              styleTag = document.createElement('style');
              styleTag.id = 'dynamic-theme';
              styleTag.className = 'aistudio-temp-theme';
              document.head.appendChild(styleTag);
            }
            const cssRules = Object.entries(theme)
              .map(([key, value]) => {
                if (key.includes('font')) {
                  loadGoogleFont(value);
                }
                return `${key}: ${value};`;
              })
              .join('\n');
            styleTag.textContent = `:root {\n${cssRules}\n}`;
          }
          const darkTheme = event.data.darkTheme;
          if (darkTheme) {
            let styleTag = document.getElementById('dynamic-dark-theme');
            if (!styleTag) {
              styleTag = document.createElement('style');
              styleTag.id = 'dynamic-dark-theme';
              styleTag.className = 'aistudio-temp-theme';
              document.head.appendChild(styleTag);
            }
            const cssRules = Object.entries(darkTheme)
              .map(([key, value]) => {
                if (key.includes('font')) {
                  loadGoogleFont(value);
                }
                return `${key}: ${value};`;
              })
              .join('\n');
            styleTag.textContent = `.dark {\n${cssRules}\n}`;
          }
        } catch (e) {}
        break;
    }
  });

  window.addEventListener('keydown', async (event) => {
    if (event.key === 'Escape' && window.aistudio?.handleFullscreenEsc) {
      const hostPort = (await bootstrapChannel).port;
      hostPort.postMessage({type: 'exit-fullscreen'});
    }
  });
})();
