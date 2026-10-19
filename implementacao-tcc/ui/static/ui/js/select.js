(function () {
  "use strict";

  var PAGE_SIZE = 10;
  var MARGIN = 12;
  var MIN_LIST = 180;

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
    this.remove = root.querySelector("[data-select-remove]");
    this.chips = root.querySelector("[data-select-chips]");
    this.control = root.querySelector("[data-select-control]");
    this.multiple = this.native.multiple;
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

  State.prototype.selectedOptions = function () {
    return Array.prototype.filter.call(this.native.options, function (option) {
      return option.selected && option.value !== "";
    });
  };

  State.prototype.isChosen = function (value) {
    return this.selectedOptions().some(function (option) {
      return option.value === value;
    });
  };

  State.prototype.selectedLabel = function () {
    var chosen = this.selectedOptions();
    if (!this.multiple) {
      var option = this.native.options[this.native.selectedIndex];
      return option ? option.text : "";
    }
    var data = this.native.dataset;
    if (!chosen.length) {
      return data.selectNone || "";
    }
    if (chosen.length === 1) {
      return "1 " + (data.selectOne || "");
    }
    return chosen.length + " " + (data.selectMany || "");
  };

  State.prototype.updateChips = function () {
    var state = this;
    if (!this.chips) {
      return;
    }
    var chosen = this.selectedOptions();
    this.chips.textContent = "";
    chosen.forEach(function (option) {
      var chip = document.createElement("li");
      chip.className = "select-chip";
      var label = document.createElement("span");
      label.textContent = option.text;
      var button = document.createElement("button");
      button.className = "select-chip-remove";
      button.type = "button";
      button.dataset.value = option.value;
      button.setAttribute("aria-label", "Retirar " + option.text);
      button.appendChild(state.remove.content.cloneNode(true));
      chip.appendChild(label);
      chip.appendChild(button);
      state.chips.appendChild(chip);
    });
  };

  State.prototype.updateTrigger = function () {
    var chosen = this.selectedOptions().length;
    var value = this.trigger.querySelector("[data-select-value]");
    value.textContent = this.selectedLabel();
    this.trigger.dataset.empty = chosen ? "false" : "true";
    if (this.multiple) {
      value.classList.toggle("sr-only", chosen > 0);
    }
    this.updateChips();
  };

  State.prototype.optionId = function (index) {
    return this.native.id + "_opcao_" + index;
  };

  State.prototype.render = function (activeIndex) {
    var state = this;
    var visible = this.options.slice(0, this.shown);
    var scroll = this.list.scrollTop;
    this.list.textContent = "";
    visible.forEach(function (option, index) {
      var item = document.createElement("li");
      item.className = "select-option";
      item.id = state.optionId(index);
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", state.isChosen(option.valor) ? "true" : "false");
      item.dataset.value = option.valor;
      var label = document.createElement("span");
      label.textContent = option.rotulo;
      label.title = option.rotulo;
      item.appendChild(label);
      if (state.isChosen(option.valor)) {
        item.appendChild(state.check.content.cloneNode(true));
      }
      state.list.appendChild(item);
    });
    this.empty.hidden = visible.length > 0;
    this.more.hidden = !(this.hasMore || this.shown < this.options.length);
    if (activeIndex === undefined) {
      this.highlight(visible.length ? 0 : -1);
    } else {
      this.list.scrollTop = scroll;
      this.highlight(Math.min(activeIndex, visible.length - 1));
    }
    this.place();
  };

  State.prototype.place = function () {
    if (this.panel.hidden) {
      return;
    }
    var anchor = (this.control || this.trigger).getBoundingClientRect();
    var below = window.innerHeight - anchor.bottom - MARGIN;
    var above = anchor.top - MARGIN;
    var chrome = this.panel.offsetHeight - this.list.offsetHeight;
    var up = below < MIN_LIST + chrome && above > below;
    if (up) {
      this.panel.dataset.drop = "up";
      this.releaseControl();
    } else {
      delete this.panel.dataset.drop;
      this.anchorControl();
    }
    var room = (up ? above : below) - chrome;
    this.list.style.maxHeight = Math.max(MIN_LIST, room) + "px";
  };

  State.prototype.anchorControl = function () {
    if (!this.control || this.root.dataset.open === "true") {
      return;
    }
    this.root.style.minHeight = this.control.offsetHeight + "px";
    this.root.dataset.open = "true";
  };

  State.prototype.releaseControl = function () {
    if (!this.control) {
      return;
    }
    delete this.root.dataset.open;
    this.root.style.minHeight = "";
  };

  State.prototype.liftModal = function () {
    var modal = this.root.closest("dialog.modal");
    if (modal && modal.scrollHeight <= modal.clientHeight) {
      modal.dataset.selectOpen = "true";
    }
  };

  State.prototype.dropModal = function () {
    var modal = this.root.closest("dialog.modal");
    if (modal) {
      delete modal.dataset.selectOpen;
    }
  };

  State.prototype.ensureRoom = function () {
    var element = this.control || this.trigger;
    var chrome = this.panel.offsetHeight - this.list.offsetHeight;
    var anchor = element.getBoundingClientRect();
    if (window.innerHeight - anchor.bottom < MIN_LIST + chrome + MARGIN) {
      element.scrollIntoView({ block: "center" });
    }
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
      var previous = this.shown;
      this.shown = Math.min(append ? this.shown + PAGE_SIZE : PAGE_SIZE, this.options.length);
      this.render(append ? previous : undefined);
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
        var previous = state.options.length;
        state.options = append ? state.options.concat(data.opcoes) : data.opcoes;
        state.hasMore = data.tem_mais;
        state.shown = state.options.length;
        state.render(append ? previous : undefined);
      });
  };

  State.prototype.open = function () {
    this.liftModal();
    this.panel.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
    this.search.value = "";
    this.term = "";
    this.ensureRoom();
    this.load(false);
    this.place();
    this.search.focus();
  };

  State.prototype.close = function (focusTrigger) {
    this.panel.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
    this.dropModal();
    this.releaseControl();
    if (focusTrigger) {
      this.trigger.focus();
    }
  };

  State.prototype.choose = function (value) {
    if (!this.multiple) {
      this.native.value = value;
      this.announce();
      this.close(true);
      return;
    }
    var option = Array.prototype.find.call(this.native.options, function (candidate) {
      return candidate.value === value;
    });
    if (!option) {
      option = new Option(this.options.find(function (candidate) {
        return candidate.valor === value;
      }).rotulo, value);
      this.native.add(option);
    }
    option.selected = !option.selected;
    this.announce();
    this.render(Math.max(this.active, 0));
  };

  State.prototype.discard = function (value) {
    Array.prototype.forEach.call(this.native.options, function (option) {
      if (option.value === value) {
        option.selected = false;
      }
    });
    this.announce();
    if (!this.panel.hidden) {
      this.render(Math.max(this.active, 0));
    }
  };

  State.prototype.announce = function () {
    this.native.dispatchEvent(new Event("change", { bubbles: true }));
    this.updateTrigger();
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
      if (state.control) {
        state.control.hidden = false;
      } else {
        state.trigger.hidden = false;
      }
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
    var chip = event.target.closest(".select-chip-remove");
    if (chip) {
      stateFor(chip).discard(chip.dataset.value);
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
        var position = state.active;
        state.choose(item.dataset.value);
        if (state.multiple) {
          state.highlight(position);
        }
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

  document.addEventListener("htmx:load", function (event) {
    init(event.target);
  });
})();
