/**
 * VKL Order Converter - LAN Sync Shim
 * Injected automatically by the Go server into <head>.
 * Enables shared SKU master across all office LAN users via /api/master.
 */
(function() {
  'use strict';

  var MASTER_KEY = 'vkl_master_v2';
  var PIN_KEY = 'vkl_pin';
  var isSyncingToServer = false;

  // Helper: Show navy corporate toast in bottom-right
  function showToast(message, isError) {
    try {
      var id = 'vkl-lan-toast';
      var existing = document.getElementById(id);
      if (existing) {
        existing.remove();
      }
      var toast = document.createElement('div');
      toast.id = id;
      toast.style.position = 'fixed';
      toast.style.bottom = '20px';
      toast.style.right = '20px';
      toast.style.zIndex = '999999';
      toast.style.backgroundColor = isError ? '#8b1e1e' : '#0B1F3A';
      toast.style.color = '#ffffff';
      toast.style.padding = '10px 18px';
      toast.style.borderRadius = '6px';
      toast.style.fontFamily = 'Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif';
      toast.style.fontSize = '13px';
      toast.style.fontWeight = '500';
      toast.style.boxShadow = '0 4px 14px rgba(0,0,0,0.25)';
      toast.style.border = isError ? '1px solid #d32f2f' : '1px solid #4A7FB5';
      toast.style.display = 'flex';
      toast.style.alignItems = 'center';
      toast.style.gap = '8px';
      toast.style.transition = 'opacity 0.3s ease';
      toast.textContent = message;

      document.body.appendChild(toast);
      setTimeout(function() {
        toast.style.opacity = '0';
        setTimeout(function() {
          if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
          }
        }, 300);
      }, 4000);
    } catch (e) {
      // Never throw
    }
  }

  // 1. Run before the tool starts: the server places the current shared master straight into this page
  //    (no network call needed, so it cannot be slow or fail). If there is none, the tool keeps its own.
  try {
    var shared = /*__VKL_SHARED_MASTER__*/null;
    if (shared && Array.isArray(shared.list) && shared.list.length > 0) {
      localStorage.setItem(MASTER_KEY, JSON.stringify(shared));
    }
  } catch (err) {
    // never throw
  }

  // 2. Wrap Storage.prototype.setItem to intercept vkl_master_v2 updates
  var originalSetItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function(key, value) {
    try {
      originalSetItem.apply(this, arguments);
    } catch (e) {
      // Re-throw quota errors or default behavior
      throw e;
    }

    if (key === MASTER_KEY && !isSyncingToServer) {
      try {
        var data = typeof value === 'string' ? JSON.parse(value) : value;
        if (data && Array.isArray(data.list) && data.list.length > 0) {
          sendMasterToServer(typeof value === 'string' ? value : JSON.stringify(value), data.list.length);
        }
      } catch (err) {
        // Not JSON or parse failure, ignore silently
      }
    }
  };

  function sendMasterToServer(payloadJson, skuCount, isRetry) {
    try {
      var pin = sessionStorage.getItem(PIN_KEY) || '';
      var putXhr = new XMLHttpRequest();
      putXhr.open('PUT', '/api/master', true); // async to not freeze UI
      putXhr.setRequestHeader('Content-Type', 'application/json');
      if (pin) {
        putXhr.setRequestHeader('X-VKL-Pin', pin);
      }

      putXhr.onload = function() {
        if (putXhr.status === 200 || putXhr.status === 204) {
          showToast('Master shared with all users (' + skuCount.toLocaleString() + ' SKUs)', false);
        } else if (putXhr.status === 401) {
          if (!isRetry) {
            var inputPin = prompt('Server PIN required to update shared ERP master:');
            if (inputPin !== null && inputPin.trim().length > 0) {
              sessionStorage.setItem(PIN_KEY, inputPin.trim());
              sendMasterToServer(payloadJson, skuCount, true);
              return;
            }
          }
          showToast('Could not share master: PIN required or invalid', true);
        } else {
          var errMsg = 'HTTP ' + putXhr.status;
          try {
            var resp = JSON.parse(putXhr.responseText);
            if (resp && resp.error) errMsg = resp.error;
          } catch(e) {}
          showToast('Could not share master: ' + errMsg, true);
        }
      };

      putXhr.onerror = function() {
        showToast('Could not share master: server unreachable', true);
      };

      putXhr.send(payloadJson);
    } catch (e) {
      // Never throw
    }
  }

  // 4. Add small grey footer line: "Served from <hostname> | build <version>"
  function appendServerFooter() {
    try {
      var hXhr = new XMLHttpRequest();
      hXhr.open('GET', '/api/health', true);
      hXhr.onload = function() {
        if (hXhr.status === 200) {
          try {
            var info = JSON.parse(hXhr.responseText);
            var host = info.host || window.location.hostname || 'LAN Server';
            var ver = info.version || '1.0.0';
            var footer = document.createElement('div');
            footer.id = 'vkl-server-footer';
            footer.style.textAlign = 'center';
            footer.style.padding = '12px 16px';
            footer.style.fontSize = '11px';
            footer.style.color = '#718096';
            footer.style.letterSpacing = '0.02em';
            footer.style.borderTop = '1px solid #E2E8F0';
            footer.style.backgroundColor = '#F8FAFC';
            footer.textContent = 'Served from ' + host + ' | build ' + ver;
            document.body.appendChild(footer);
          } catch (e) {}
        }
      };
      hXhr.send(null);
    } catch (e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', appendServerFooter);
  } else {
    appendServerFooter();
  }
})();
