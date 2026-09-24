(function () {
  "use strict";

  var RETRY_MIN = 1000;
  var RETRY_MAX = 30000;
  var retry = RETRY_MIN;

  function panels() {
    return document.querySelectorAll("[data-notifications]");
  }

  function applyFilter(panel) {
    var unreadButton = panel.querySelector('[data-show="unread"]');
    if (!unreadButton) {
      return;
    }
    var onlyUnread = unreadButton.getAttribute("aria-pressed") === "true";
    var visible = 0;
    panel.querySelectorAll(".notification").forEach(function (item) {
      var show = !onlyUnread || item.classList.contains("is-unread");
      item.hidden = !show;
      visible += show ? 1 : 0;
    });
    panel.querySelector("[data-empty]").hidden = visible > 0;
  }

  function bind(panel) {
    var filter = panel.querySelector("[data-filter]");
    if (!filter) {
      return;
    }
    filter.hidden = false;
    filter.querySelectorAll("button").forEach(function (button) {
      button.addEventListener("click", function () {
        filter.querySelectorAll("button").forEach(function (other) {
          other.setAttribute("aria-pressed", String(other === button));
        });
        applyFilter(panel);
      });
    });
  }

  function refresh() {
    var first = document.querySelector("[data-notifications]");
    if (!first) {
      return;
    }
    fetch(first.dataset.notificationsPanel, { credentials: "same-origin" })
      .then(function (response) {
        return response.ok ? response.text() : Promise.reject(response.status);
      })
      .then(function (html) {
        var fresh = new DOMParser().parseFromString(html, "text/html").querySelector("[data-notifications]");
        if (!fresh) {
          return;
        }
        panels().forEach(function (panel) {
          var open = panel.open;
          panel.innerHTML = fresh.innerHTML;
          panel.open = open;
          bind(panel);
        });
      })
      .catch(function () {});
  }

  function listen() {
    var first = document.querySelector("[data-notifications]");
    if (!first || !window.WebSocket) {
      return;
    }
    var scheme = window.location.protocol === "https:" ? "wss://" : "ws://";
    var socket = new WebSocket(scheme + window.location.host + first.dataset.notificationsChannel);

    socket.addEventListener("open", function () {
      retry = RETRY_MIN;
      refresh();
    });

    socket.addEventListener("message", function () {
      refresh();
    });

    socket.addEventListener("close", function () {
      window.setTimeout(listen, retry);
      retry = Math.min(retry * 2, RETRY_MAX);
    });
  }

  panels().forEach(bind);
  listen();
})();
