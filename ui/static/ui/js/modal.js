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

  function closeWithAnimation(dialog) {
    if (dialog.classList.contains("is-closing")) {
      return;
    }
    dialog.classList.add("is-closing");
    var finish = function () {
      if (dialog.open) {
        dialog.close();
      }
    };
    dialog.addEventListener("animationend", finish, { once: true });
    window.setTimeout(finish, 400);
  }

  var replacing = false;

  document.addEventListener("htmx:beforeSwap", function (event) {
    replacing = event.detail.target.id === "modal" && !!event.detail.target.querySelector("dialog[open]");
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    var container = document.getElementById("modal");
    if (event.detail.target === container && !container.contains(event.detail.elt) && event.detail.elt !== document.body) {
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
    if (replacing) {
      dialog.classList.add("is-replaced");
    }
    dialog.addEventListener("click", function (click) {
      if (click.target.closest("[data-modal-close]")) {
        closeWithAnimation(dialog);
      }
    });
    dialog.addEventListener("cancel", function (cancel) {
      cancel.preventDefault();
      closeWithAnimation(dialog);
    });
    dialog.addEventListener("keydown", function (key) {
      keepFocusInside(dialog, key);
    });
    dialog.addEventListener("close", function () {
      if (dialog.hasAttribute("data-reload-on-close")) {
        window.location.reload();
        return;
      }
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
