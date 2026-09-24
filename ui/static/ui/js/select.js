(function () {
  "use strict";

  var PAGE_SIZE = 10;

  function normalize(text) {
    return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function State(root) {
    this.root = root;
    this.native = root.querySelector("select");
    this.trigger = root.querySelector("[data-select-trigger]");
    this.panel = root.querySelector("[data-select-panel]");
    this.searchWrap = root.querySelector("[data-select-search-wrap]");
    this.search = root.querySelector("[data-select-search]");
    this.list = root.querySelector("[data-select-options]");
    this.empty = root.querySelector("[data-select-empty]");
    this.more = root.querySelector("[data-select-more]");
    this.check = root.querySelector("[data-select-check]");
    this.source = this.native.dataset.selectSource || "";
    this.options = [];
    this.shown = 0;
    this.hasMore = false;
    this.term = "";
    this.active = -1;
    this.requestId = 0;
  }

  State.prototype.nativeOptions = function () {
    return Array.prototype.map.call(this.native.options, function (option) {
      return { valor: option.value, rotulo: option.text };
    });
  };

  State.prototype.selectedLabel = function () {
    var option = this.native.options[this.native.selectedIndex];
    return option ? option.text : "";
  };

  State.prototype.updateTrigger = function () {
    this.trigger.querySelector("[data-select-value]").textContent = this.selectedLabel();
    this.trigger.dataset.empty = this.native.value === "" ? "true" : "false";
  };

  State.prototype.optionId = function (index) {
    return this.native.id + "_opcao_" + index;
  };

  State.prototype.render = function () {
    var state = this;
    var visible = this.options.slice(0, this.shown);
    this.list.textContent = "";
    visible.forEach(function (option, index) {
      var item = document.createElement("li");
      item.className = "select-option";
      item.id = state.optionId(index);
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", option.valor === state.native.value ? "true" : "false");
      item.dataset.value = option.valor;
      var label = document.createElement("span");
      label.textContent = option.rotulo;
      item.appendChild(label);
      if (option.valor === state.native.value) {
        item.appendChild(state.check.content.cloneNode(true));
      }
      state.list.appendChild(item);
    });
    this.empty.hidden = visible.length > 0;
    this.more.hidden = !(this.hasMore || this.shown < this.options.length);
    this.highlight(visible.length ? 0 : -1);
  };

  State.prototype.highlight = function (index) {
    this.active = index;
    var items = this.list.querySelectorAll(".select-option");
    items.forEach(function (item, position) {
      item.dataset.active = position === index ? "true" : "false";
    });
    if (index >= 0 && items[index]) {
      this.search.setAttribute("aria-activedescendant", items[index].id);
      items[index].scrollIntoView({ block: "nearest" });
    } else {
      this.search.removeAttribute("aria-activedescendant");
    }
  };

  State.prototype.move = function (step) {
    var items = this.list.querySelectorAll(".select-option");
    if (!items.length) {
      return;
    }
    var next = this.active + step;
    if (next < 0) {
      next = items.length - 1;
    }
    if (next >= items.length) {
      next = 0;
    }
    this.highlight(next);
  };

  State.prototype.load = function (append) {
    var state = this;
    if (!this.source) {
      var term = normalize(this.term.trim());
      var all = this.nativeOptions();
      this.options = term
        ? all.filter(function (option) { return normalize(option.rotulo).indexOf(term) !== -1; })
        : all;
      this.hasMore = false;
      this.shown = Math.min(append ? this.shown + PAGE_SIZE : PAGE_SIZE, this.options.length);
      this.render();
      return;
    }
    var page = append ? Math.floor(this.shown / PAGE_SIZE) + 1 : 1;
    var request = ++this.requestId;
    var url = this.source + "?busca=" + encodeURIComponent(this.term.trim()) + "&pagina=" + page;
    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (response) { return response.ok ? response.json() : { opcoes: [], tem_mais: false }; })
      .then(function (data) {
        if (request !== state.requestId) {
          return;
        }
        state.options = append ? state.options.concat(data.opcoes) : data.opcoes;
        state.hasMore = data.tem_mais;
        state.shown = state.options.length;
        state.render();
      });
  };

  State.prototype.open = function () {
    this.panel.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
    this.search.value = "";
    this.term = "";
    this.load(false);
    this.search.focus();
    this.panel.scrollIntoView({ block: "nearest" });
  };

  State.prototype.close = function (focusTrigger) {
    this.panel.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
    if (focusTrigger) {
      this.trigger.focus();
    }
  };

  State.prototype.choose = function (value) {
    this.native.value = value;
    this.native.dispatchEvent(new Event("change", { bubbles: true }));
    this.updateTrigger();
    this.close(true);
  };

  function stateFor(element) {
    var root = element.closest ? element.closest("[data-select]") : null;
    return root ? root.selectState : null;
  }

  function openStates() {
    return Array.prototype.filter.call(
      document.querySelectorAll("[data-select]"),
      function (root) { return root.selectState && !root.selectState.panel.hidden; }
    ).map(function (root) { return root.selectState; });
  }

  function init(root) {
    root.querySelectorAll("[data-select]").forEach(function (element) {
      if (element.dataset.ready) {
        return;
      }
      element.dataset.ready = "true";
      var state = new State(element);
      element.selectState = state;
      element.querySelector(".select-native").hidden = true;
      state.trigger.hidden = false;
      state.searchWrap.hidden = state.native.options.length <= PAGE_SIZE && !state.source;
      state.updateTrigger();
      state.native.addEventListener("change", function () {
        state.updateTrigger();
      });
    });
  }

  document.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-select-trigger]");
    if (trigger) {
      var state = stateFor(trigger);
      if (state.panel.hidden) {
        state.open();
      } else {
        state.close(true);
      }
      return;
    }
    var option = event.target.closest(".select-option");
    if (option) {
      stateFor(option).choose(option.dataset.value);
      return;
    }
    if (event.target.closest("[data-select-more]")) {
      stateFor(event.target).load(true);
      return;
    }
    openStates().forEach(function (state) {
      if (!state.root.contains(event.target)) {
        state.close(false);
      }
    });
  });

  document.addEventListener("input", function (event) {
    if (event.target.matches("[data-select-search]")) {
      var state = stateFor(event.target);
      state.term = event.target.value;
      state.load(false);
    }
  });

  document.addEventListener("keydown", function (event) {
    var state = stateFor(event.target);
    if (!state || state.panel.hidden) {
      if (state && event.key === "ArrowDown" && event.target.matches("[data-select-trigger]")) {
        event.preventDefault();
        state.open();
      }
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      state.move(event.key === "ArrowDown" ? 1 : -1);
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      state.highlight(event.key === "Home" ? 0 : state.list.querySelectorAll(".select-option").length - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      var item = state.list.querySelectorAll(".select-option")[state.active];
      if (item) {
        state.choose(item.dataset.value);
      }
    } else if (event.key === "Escape") {
      event.preventDefault();
      state.close(true);
    } else if (event.key === "Tab") {
      state.close(false);
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    init(event.detail.target);
  });
})();
