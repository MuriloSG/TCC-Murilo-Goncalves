(function () {
  "use strict";

  var STORAGE_KEY = "tema";
  var DARK = "escuro";
  var LIGHT = "claro";

  function stored() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
  }

  function save(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      return;
    }
  }

  function current() {
    return document.documentElement.dataset.theme === "light" ? LIGHT : DARK;
  }

  function apply(theme) {
    document.documentElement.dataset.theme = theme === LIGHT ? "light" : "dark";
  }

  function sync() {
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    var label = current() === DARK ? "Ativar o modo claro" : "Ativar o modo escuro";
    Array.prototype.forEach.call(buttons, function (button) {
      button.setAttribute("aria-label", label);
      var tip = button.querySelector(".tip");
      if (tip) {
        tip.textContent = label;
      }
      button.hidden = false;
    });
  }

  apply(stored() === LIGHT ? LIGHT : DARK);

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-theme-toggle]");
    if (!button) {
      return;
    }
    var theme = current() === DARK ? LIGHT : DARK;
    apply(theme);
    save(theme);
    sync();
  });

  document.addEventListener("DOMContentLoaded", sync);
  document.addEventListener("htmx:load", sync);
})();
