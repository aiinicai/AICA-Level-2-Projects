/**
 * Shared modal accessibility layer.
 *
 * The app opens and closes its seven modals by writing `style.display` from
 * ~20 call sites across five files. Rather than rewrite all of them, this
 * observes visibility and layers on the keyboard behaviour that was missing:
 * Escape to dismiss, a focus trap, focus restore, backdrop dismissal, and the
 * dialog ARIA roles. Every existing call site keeps working untouched.
 *
 * Modals that must not be dismissible carry `data-modal-persistent`.
 */
(function () {
    'use strict';

    var FOCUSABLE = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled]):not([type="hidden"])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[tabindex]:not([tabindex="-1"])'
    ].join(',');

    // Modals currently visible, oldest first. Escape and the focus trap always
    // act on the last entry, so stacked dialogs behave predictably.
    var stack = [];

    function isVisible(modal) {
        return window.getComputedStyle(modal).display !== 'none';
    }

    function focusableWithin(modal) {
        return Array.prototype.filter.call(
            modal.querySelectorAll(FOCUSABLE),
            function (el) {
                return el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement;
            }
        );
    }

    function dismiss(modal) {
        if (modal.hasAttribute('data-modal-persistent')) return;

        // Always dismiss through a control the app already wired, never by
        // hiding the element. `customAlert` / `customConfirm` return a promise
        // that only settles in a button handler, so hiding their dialog
        // directly would leave every awaiting caller hanging forever.
        var trigger = modal.querySelector('.close') ||
                      modal.querySelector('[data-modal-dismiss]');

        if (!trigger) {
            var buttons = Array.prototype.slice.call(
                modal.querySelectorAll('button:not([disabled])')
            );
            // A cancel-shaped control is the correct Escape outcome.
            trigger = buttons.filter(function (btn) {
                return /cancel|close|dismiss/i.test(btn.id + ' ' + btn.className + ' ' + btn.textContent);
            })[0];
            // Otherwise an acknowledge-only dialog (a single button, e.g. OK)
            // has exactly one outcome, so pressing it is what Escape means.
            if (!trigger && buttons.length === 1) trigger = buttons[0];
        }

        if (trigger) {
            trigger.click();
            // The handler may be bound later than boot (agents.js binds .close
            // during post-login init), so confirm it actually closed.
            if (!isVisible(modal)) return;
        }

        // Last resort: no control exists to route through.
        modal.style.display = 'none';
    }

    function onOpen(modal) {
        if (stack.indexOf(modal) !== -1) return;

        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');

        // Name the dialog from its own heading so screen readers announce it.
        var heading = modal.querySelector('.modal-header h2, .modal-header h3');
        if (heading) {
            if (!heading.id) {
                heading.id = 'modal-heading-' + (modal.id || Math.random().toString(36).slice(2));
            }
            modal.setAttribute('aria-labelledby', heading.id);
        }

        modal._restoreFocusTo = document.activeElement;
        stack.push(modal);
        document.body.style.overflow = 'hidden';

        // Focus the first meaningful control, not the close button, so keyboard
        // users land where the task is.
        var targets = focusableWithin(modal);
        var preferred = targets.filter(function (el) {
            return !el.classList.contains('close');
        });
        var first = preferred[0] || targets[0];
        if (first) {
            // Defer: content is often injected right after display is set.
            window.setTimeout(function () {
                if (isVisible(modal)) first.focus();
            }, 0);
        }
    }

    function onClose(modal) {
        var i = stack.indexOf(modal);
        if (i === -1) return;
        stack.splice(i, 1);

        modal.removeAttribute('aria-modal');

        if (!stack.length) document.body.style.overflow = '';

        var restore = modal._restoreFocusTo;
        modal._restoreFocusTo = null;
        if (restore && document.contains(restore) && typeof restore.focus === 'function') {
            restore.focus();
        }
    }

    function watch(modal) {
        if (modal._a11yWatched) return;
        modal._a11yWatched = true;

        var observer = new MutationObserver(function () {
            if (isVisible(modal)) onOpen(modal);
            else onClose(modal);
        });
        observer.observe(modal, { attributes: true, attributeFilter: ['style', 'class'] });

        if (isVisible(modal)) onOpen(modal);
    }

    function watchAll() {
        Array.prototype.forEach.call(document.querySelectorAll('.modal'), watch);
    }

    document.addEventListener('keydown', function (event) {
        if (!stack.length) return;
        var modal = stack[stack.length - 1];

        if (event.key === 'Escape') {
            if (modal.hasAttribute('data-modal-persistent')) return;
            event.preventDefault();
            dismiss(modal);
            return;
        }

        if (event.key !== 'Tab') return;

        var targets = focusableWithin(modal);
        if (!targets.length) {
            event.preventDefault();
            return;
        }

        var first = targets[0];
        var last = targets[targets.length - 1];

        // Focus escaped the dialog entirely (injected content, stray click).
        if (!modal.contains(document.activeElement)) {
            event.preventDefault();
            first.focus();
            return;
        }

        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    // Backdrop dismissal. `#settings-modal` already has its own handler in
    // auth.js that runs the proper teardown, so it is left alone here.
    document.addEventListener('mousedown', function (event) {
        if (!stack.length) return;
        var modal = stack[stack.length - 1];
        if (modal.id === 'settings-modal') return;
        if (event.target === modal) dismiss(modal);
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', watchAll);
    } else {
        watchAll();
    }

    // Modals added after boot (none today, but the results renderers rebuild
    // their contents and future work may inject dialogs).
    new MutationObserver(watchAll).observe(document.documentElement, {
        childList: true,
        subtree: true
    });
})();
