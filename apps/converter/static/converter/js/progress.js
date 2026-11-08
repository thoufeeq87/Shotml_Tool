// Progress page: poll the batch and show "2 of 5 done" with a status for each screenshot.
(function () {
  "use strict";

  var POLL_MS = 2000;
  var app = document.getElementById("progress-app");
  if (!app) return;

  var text = document.getElementById("progress-text");
  var fill = document.getElementById("progress-fill");
  var errorBox = document.getElementById("progress-error");

  var LABELS = { pending: "Waiting", working: "Working", done: "Done", failed: "Failed" };

  function showSlot(slot) {
    var row = app.querySelector('[data-slot="' + slot.position + '"]');
    if (!row) return;
    var badge = row.querySelector("[data-status-badge]");
    badge.textContent = LABELS[slot.status] || slot.status;
    badge.className = "nb-tag nb-status-" + slot.status;
  }

  function update(data) {
    text.textContent = data.done + " of " + data.total + " done";
    fill.style.width = (data.total ? (data.done / data.total) * 100 : 0) + "%";
    data.slots.forEach(showSlot);
  }

  function poll() {
    fetch(app.dataset.statusUrl)
      .then(function (response) {
        if (!response.ok) throw new Error("bad status");
        return response.json();
      })
      .then(function (data) {
        errorBox.hidden = true;
        update(data);
        if (data.status === "done") {
          window.location.href = app.dataset.resultsUrl;
          return;
        }
        setTimeout(poll, POLL_MS);
      })
      .catch(function () {
        errorBox.hidden = false;
        setTimeout(poll, POLL_MS);
      });
  }

  poll();
})();
