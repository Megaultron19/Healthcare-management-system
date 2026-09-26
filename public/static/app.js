(function () {
  // Confirm before destructive actions.
  document.addEventListener("submit", function (e) {
    var msg = e.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // Status dropdowns save as soon as they change.
  document.querySelectorAll("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });

  // Clickable table rows (ignore clicks on links, buttons and form controls).
  document.querySelectorAll("tr[data-href]").forEach(function (row) {
    row.addEventListener("click", function (e) {
      if (e.target.closest("a, button, input, select, form")) return;
      window.location = row.getAttribute("data-href");
    });
  });

  // Tabs on the patient page, synced with the URL hash.
  var tabs = document.querySelectorAll(".tabs [data-tab]");
  if (tabs.length) {
    var show = function (name) {
      var found = false;
      tabs.forEach(function (t) {
        var on = t.getAttribute("data-tab") === name;
        found = found || on;
        t.classList.toggle("active", on);
        t.setAttribute("aria-selected", on);
        document.getElementById("tab-" + t.getAttribute("data-tab")).classList.toggle("active", on);
      });
      return found;
    };
    tabs.forEach(function (t) {
      t.addEventListener("click", function () {
        var name = t.getAttribute("data-tab");
        show(name);
        history.replaceState(null, "", "#" + name);
      });
    });
    if (!show(location.hash.slice(1))) show(tabs[0].getAttribute("data-tab"));
  }

  // Flash messages fade away after a few seconds.
  setTimeout(function () {
    document.querySelectorAll(".flash-success, .flash-info").forEach(function (el) { el.remove(); });
  }, 6000);
})();
