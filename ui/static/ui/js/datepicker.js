(function () {
  "use strict";

  var MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  var WEEKDAYS = ["D", "S", "T", "Q", "Q", "S", "S"];
  var WEEKDAY_NAMES = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"];

  function pad(number) {
    return (number < 10 ? "0" : "") + number;
  }

  function iso(day) {
    return day.getFullYear() + "-" + pad(day.getMonth() + 1) + "-" + pad(day.getDate());
  }

  function parse(value) {
    var parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
    return parts ? new Date(+parts[1], +parts[2] - 1, +parts[3]) : null;
  }

  function button(className, label, content) {
    var element = document.createElement("button");
    element.type = "button";
    element.className = className;
    element.setAttribute("aria-label", label);
    element.appendChild(content);
    return element;
  }

  function State(root) {
    this.root = root;
    this.input = root.querySelector("input");
    this.trigger = root.querySelector("[data-date-trigger]");
    this.panel = root.querySelector("[data-date-panel]");
    this.focused = null;
  }

  State.prototype.inRange = function (day) {
    var min = parse(this.input.min);
    var max = parse(this.input.max);
    return !(min && day < min) && !(max && day > max);
  };

  State.prototype.render = function () {
    var state = this;
    var focused = this.focused;
    var selected = iso(parse(this.input.value) || new Date(0));
    var today = iso(new Date());
    this.panel.textContent = "";

    var head = document.createElement("div");
    head.className = "date-head";
    var title = document.createElement("p");
    title.className = "date-title";
    title.setAttribute("aria-live", "polite");
    title.textContent = MONTHS[focused.getMonth()] + " de " + focused.getFullYear();
    var prev = button("icon-btn", "Mês anterior", this.root.querySelector("[data-date-prev]").content.cloneNode(true));
    prev.dataset.dateStep = "-1";
    var next = button("icon-btn", "Próximo mês", this.root.querySelector("[data-date-next]").content.cloneNode(true));
    next.dataset.dateStep = "1";
    head.appendChild(prev);
    head.appendChild(title);
    head.appendChild(next);
    this.panel.appendChild(head);

    var grid = document.createElement("div");
    grid.className = "date-grid";
    grid.setAttribute("role", "grid");
    WEEKDAYS.forEach(function (letter, index) {
      var cell = document.createElement("abbr");
      cell.className = "date-weekday";
      cell.title = WEEKDAY_NAMES[index];
      cell.textContent = letter;
      grid.appendChild(cell);
    });
    var first = new Date(focused.getFullYear(), focused.getMonth(), 1);
    for (var blank = 0; blank < first.getDay(); blank++) {
      grid.appendChild(document.createElement("span"));
    }
    var last = new Date(focused.getFullYear(), focused.getMonth() + 1, 0).getDate();
    for (var number = 1; number <= last; number++) {
      var day = new Date(focused.getFullYear(), focused.getMonth(), number);
      var value = iso(day);
      var cell = document.createElement("button");
      cell.type = "button";
      cell.className = "date-day";
      cell.textContent = number;
      cell.dataset.dateValue = value;
      cell.setAttribute("aria-label", WEEKDAY_NAMES[day.getDay()] + ", " + number + " de " + MONTHS[day.getMonth()]);
      cell.tabIndex = number === focused.getDate() ? 0 : -1;
      cell.disabled = !state.inRange(day);
      if (value === selected) {
        cell.setAttribute("aria-pressed", "true");
      }
      if (value === today) {
        cell.setAttribute("aria-current", "date");
      }
      grid.appendChild(cell);
    }
    this.panel.appendChild(grid);
  };

  State.prototype.focusDay = function () {
    var cell = this.panel.querySelector("[tabindex='0']");
    if (cell) {
      cell.focus();
    }
  };

  State.prototype.open = function () {
    this.focused = parse(this.input.value) || new Date();
    this.render();
    this.panel.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
    this.focusDay();
  };

  State.prototype.close = function (focusTrigger) {
    this.panel.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
    if (focusTrigger) {
      this.trigger.focus();
    }
  };

  State.prototype.move = function (days, months) {
    var day = this.focused;
    this.focused = months
      ? new Date(day.getFullYear(), day.getMonth() + months, Math.min(day.getDate(), new Date(day.getFullYear(), day.getMonth() + months + 1, 0).getDate()))
      : new Date(day.getFullYear(), day.getMonth(), day.getDate() + days);
    this.render();
  };

  State.prototype.choose = function (value) {
    this.input.value = value;
    this.input.dispatchEvent(new Event("input", { bubbles: true }));
    this.input.dispatchEvent(new Event("change", { bubbles: true }));
    this.close(true);
  };

  function stateFor(element) {
    var root = element.closest ? element.closest("[data-date]") : null;
    return root ? root.dateState : null;
  }

  function init(root) {
    root.querySelectorAll("[data-date]").forEach(function (element) {
      if (element.dataset.ready) {
        return;
      }
      element.dataset.ready = "true";
      element.dateState = new State(element);
      element.dateState.trigger.hidden = element.dateState.input.disabled || element.dateState.input.readOnly;
    });
  }

  document.addEventListener("click", function (event) {
    var state = stateFor(event.target);
    document.querySelectorAll("[data-date]").forEach(function (root) {
      if (root.dateState && root.dateState !== state && !root.dateState.panel.hidden) {
        root.dateState.close(false);
      }
    });
    if (!state) {
      return;
    }
    if (event.target.closest("[data-date-trigger]")) {
      if (state.panel.hidden) {
        state.open();
      } else {
        state.close(true);
      }
      return;
    }
    var step = event.target.closest("[data-date-step]");
    if (step) {
      state.move(0, +step.dataset.dateStep);
      return;
    }
    var day = event.target.closest("[data-date-value]");
    if (day) {
      state.choose(day.dataset.dateValue);
    }
  });

  document.addEventListener("keydown", function (event) {
    var state = stateFor(event.target);
    if (!state || state.panel.hidden) {
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      state.close(true);
      return;
    }
    if (!event.target.matches(".date-day")) {
      return;
    }
    var moves = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [-7, 0], ArrowDown: [7, 0], PageUp: [0, -1], PageDown: [0, 1] };
    var move = moves[event.key];
    if (move) {
      event.preventDefault();
      state.move(move[0], move[1]);
      state.focusDay();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  document.addEventListener("htmx:load", function (event) {
    init(event.target);
  });
})();
