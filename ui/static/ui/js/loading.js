(function () {
  "use strict";

  var DEFAULT_MESSAGE = "Carregando";

  function dialog() {
    return document.getElementById("carregamento");
  }

  function show(message) {
    var element = dialog();
    if (!element) {
      return;
    }
    var text = element.querySelector("[data-loading-message]");
    text.textContent = message || DEFAULT_MESSAGE;
    text.classList.toggle("sr-only", !message);
    document.body.setAttribute("aria-busy", "true");
    if (!element.open) {
      element.showModal();
    }
  }

  function hide() {
    var element = dialog();
    if (element && element.open) {
      element.close();
    }
    document.body.removeAttribute("aria-busy");
  }

  function run(operation, message) {
    show(message);
    return Promise.resolve().then(operation).finally(hide);
  }

  document.addEventListener("cancel", function (event) {
    if (event.target === dialog()) {
      event.preventDefault();
    }
  }, true);

  var formPending = false;

  function tracked(form) {
    return form && form.tagName === "FORM" && form.getAttribute("data-loading") !== "false";
  }

  function startForm(form) {
    formPending = true;
    show(form.getAttribute("data-loading"));
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (tracked(form) && !form.matches("[hx-get], [hx-post]")) {
      startForm(form);
    }
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    var xhr = event.detail.xhr;
    if (!tracked(event.detail.elt)) {
      return;
    }
    startForm(event.detail.elt);
    xhr.addEventListener("loadend", function () {
      var redirect = xhr.status >= 200 && xhr.status < 400 && xhr.getResponseHeader("HX-Redirect");
      if (formPending && !redirect) {
        formPending = false;
        hide();
      }
    });
  });

  window.addEventListener("pageshow", function (event) {
    if (event.persisted) {
      formPending = false;
      hide();
    }
  });

  window.IFAgenda = window.IFAgenda || {};
  window.IFAgenda.loading = { show: show, hide: hide, run: run };
  window.showLoading = show;
  window.hideLoading = hide;
})();
