(function () {
  "use strict";

  var opener = null;

  var FOCUSABLE = "a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])";

  function keepFocusInside(dialog, event) {
    if (event.key !== "Tab") {
      return;
    }
    var items = dialog.querySelectorAll(FOCUSABLE);
    var first = items[0];
    var last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function focusTarget(element) {
    var closed = element.closest("details:not([open])");
    return closed ? closed.querySelector("summary") : element;
  }

  document.addEventListener("htmx:beforeRequest", function (event) {
    var container = document.getElementById("modal");
    if (event.detail.target === container && !container.contains(event.detail.elt)) {
      opener = event.detail.elt;
      var menu = opener.closest("details[open]");
      if (menu) {
        menu.removeAttribute("open");
      }
    }
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    var container = event.detail.target;
    if (container.id !== "modal") {
      return;
    }
    var dialog = container.querySelector("dialog");
    if (!dialog) {
      return;
    }
    dialog.addEventListener("click", function (click) {
      if (click.target.closest("[data-modal-close]")) {
        dialog.close();
      }
    });
    dialog.addEventListener("keydown", function (key) {
      keepFocusInside(dialog, key);
    });
    dialog.addEventListener("close", function () {
      container.replaceChildren();
      if (opener && document.contains(opener)) {
        focusTarget(opener).focus();
      }
      opener = null;
    });
    dialog.showModal();
    var field = dialog.querySelector('[aria-invalid="true"]') ||
      dialog.querySelector(".modal-body :is(input:not([type=hidden]), select, textarea)");
    if (field) {
      field.focus();
    }
  });
})();
