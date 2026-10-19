(function () {
  "use strict";

  function normalize(text) {
    return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function visibleBoxes(list) {
    return Array.prototype.filter.call(
      list.querySelectorAll(".check-option input[type=checkbox]"),
      function (box) { return !box.closest(".check-option").hidden; }
    );
  }

  function update(list) {
    var boxes = list.querySelectorAll(".check-option input[type=checkbox]");
    var checked = 0;
    var changed = false;
    boxes.forEach(function (box) {
      if (box.checked) {
        checked += 1;
      }
      if (box.checked !== box.defaultChecked) {
        changed = true;
      }
    });
    list.querySelector("[data-checklist-selected]").textContent = checked;
    list.querySelector("[data-checklist-unsaved]").hidden = !changed;
    list.querySelectorAll(".checklist-group").forEach(function (group) {
      var inGroup = group.querySelectorAll(".check-option input[type=checkbox]");
      var checkedInGroup = group.querySelectorAll(".check-option input[type=checkbox]:checked").length;
      group.querySelector("[data-checklist-group-count]").textContent = checkedInGroup + "/" + inGroup.length;
      var master = group.querySelector("[data-checklist-group-toggle]");
      master.checked = checkedInGroup === inGroup.length;
      master.indeterminate = checkedInGroup > 0 && checkedInGroup < inGroup.length;
    });
    var visible = visibleBoxes(list);
    var allChecked = visible.length > 0 && visible.every(function (box) { return box.checked; });
    list.querySelector("[data-checklist-toggle]").dataset.state = allChecked ? "all" : "none";
  }

  function filter(list, term) {
    var query = normalize(term.trim());
    var any = false;
    list.querySelectorAll(".checklist-group").forEach(function (group) {
      var shown = 0;
      group.querySelectorAll(".check-option").forEach(function (option) {
        var match = normalize(option.textContent).indexOf(query) !== -1;
        option.hidden = !match;
        if (match) {
          shown += 1;
        }
      });
      group.hidden = shown === 0;
      if (query && shown) {
        group.open = true;
      }
      any = any || shown > 0;
    });
    list.querySelector("[data-checklist-empty]").hidden = any;
    update(list);
  }

  function init(root) {
    root.querySelectorAll("[data-checklist]").forEach(function (list) {
      if (list.dataset.ready) {
        return;
      }
      list.dataset.ready = "true";
      list.querySelector("[data-checklist-tools]").hidden = false;
      update(list);
    });
  }

  document.addEventListener("change", function (event) {
    var list = event.target.closest("[data-checklist]");
    if (list && event.target.type === "checkbox") {
      if (event.target.matches("[data-checklist-group-toggle]")) {
        var checked = event.target.checked;
        event.target.closest(".checklist-group").querySelectorAll(".check-option input[type=checkbox]").forEach(function (box) {
          box.checked = checked;
        });
      }
      update(list);
    }
  });

  document.addEventListener("input", function (event) {
    if (event.target.matches("[data-checklist-search]")) {
      filter(event.target.closest("[data-checklist]"), event.target.value);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && event.target.matches("[data-checklist-search]")) {
      event.preventDefault();
    }
  });

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-checklist-toggle]");
    if (!toggle) {
      return;
    }
    var list = toggle.closest("[data-checklist]");
    var select = toggle.dataset.state !== "all";
    visibleBoxes(list).forEach(function (box) {
      box.checked = select;
    });
    update(list);
  });

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    init(event.detail.target);
  });
})();
