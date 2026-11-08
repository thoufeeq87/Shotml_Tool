// Shotml Tool page script: upload, progress polling, result cards, copy and download.
(function () {
  "use strict";

  var POLL_MS = 2000;
  var tool = document.getElementById("tool");
  var csrf = tool.querySelector("[name=csrfmiddlewaretoken]").value;
  var maxFiles = Number(tool.dataset.maxFiles);
  var ZERO_ID = "00000000-0000-0000-0000-000000000000";

  var form = document.getElementById("upload-form");
  var fileInput = document.getElementById("screenshots");
  var fileList = document.getElementById("file-list");
  var errorList = document.getElementById("error-list");
  var convertButton = document.getElementById("convert-button");
  var progressPanel = document.getElementById("progress-panel");
  var progressText = document.getElementById("progress-text");
  var progressFill = document.getElementById("progress-fill");
  var results = document.getElementById("results");
  var resultList = document.getElementById("result-list");
  var resultsNote = document.getElementById("results-note");

  var rendered = [];
  var pollTimer = null;

  // --- Helpers ---
  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function urlFor(template, batchId) {
    return template.replace(ZERO_ID, batchId);
  }

  function showErrors(messages) {
    errorList.innerHTML = "";
    messages.forEach(function (message) {
      errorList.appendChild(element("li", "", message));
    });
    errorList.hidden = messages.length === 0;
  }

  // --- Upload form ---
  fileInput.addEventListener("change", function () {
    fileList.innerHTML = "";
    Array.prototype.forEach.call(fileInput.files, function (file) {
      fileList.appendChild(element("li", "", file.name));
    });
    showErrors(fileInput.files.length > maxFiles ? ["You can upload up to " + maxFiles + " screenshots at a time."] : []);
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (fileInput.files.length === 0) return showErrors(["Please choose at least one screenshot."]);
    if (fileInput.files.length > maxFiles) return showErrors(["You can upload up to " + maxFiles + " screenshots at a time."]);

    showErrors([]);
    convertButton.disabled = true;
    fetch(tool.dataset.startUrl, { method: "POST", body: new FormData(form), headers: { "X-CSRFToken": csrf } })
      .then(function (response) {
        return response.json().then(function (data) { return { ok: response.ok, data: data }; });
      })
      .then(function (reply) {
        if (!reply.ok) throw new Error((reply.data.errors || ["Something went wrong. Please try again."]).join("\n"));
        beginWatching(reply.data.batch_id);
      })
      .catch(function (error) {
        showErrors(error.message.split("\n"));
        convertButton.disabled = false;
      });
  });

  // --- Progress polling ---
  function beginWatching(batchId) {
    rendered = [];
    resultList.innerHTML = "";
    results.hidden = false;
    progressPanel.hidden = false;
    poll(batchId);
  }

  function poll(batchId) {
    var url = urlFor(tool.dataset.statusUrlTemplate, batchId) + "?rendered=" + rendered.join(",");
    fetch(url)
      .then(function (response) {
        if (!response.ok) throw new Error("not found");
        return response.json();
      })
      .then(function (data) {
        updateProgress(data);
        data.slots.forEach(function (slot) {
          if ((slot.status === "done" || slot.status === "failed") && rendered.indexOf(slot.position) === -1) {
            resultList.appendChild(buildCard(slot));
            rendered.push(slot.position);
          }
        });
        if (data.status === "done") return finish(data);
        pollTimer = setTimeout(function () { poll(batchId); }, POLL_MS);
      })
      .catch(function () {
        showErrors(["We lost track of this batch. Please upload again."]);
        convertButton.disabled = false;
      });
  }

  function updateProgress(data) {
    progressText.textContent = data.done + " of " + data.total + " done";
    progressFill.style.width = (data.total ? (data.done / data.total) * 100 : 0) + "%";
  }

  function finish(data) {
    progressPanel.hidden = true;
    convertButton.disabled = false;
    resultsNote.textContent = data.keep_images
      ? "Your pictures and code are saved. Find them under \"Your kept batches\" after you reload."
      : "Your pictures were deleted. Copy or download your code now; it is not listed after you leave.";
  }

  // --- Result cards ---
  function buildCard(slot) {
    var card = element("article", "result-card");
    card.appendChild(element("h3", "result-title", "Screenshot " + slot.position + ": " + slot.name));

    if (slot.status === "failed") {
      card.appendChild(element("p", "error-text", slot.error));
      return card;
    }

    card.appendChild(element("p", "note", "Made by " + slot.provider));
    card.appendChild(buildPreview(slot));
    card.appendChild(buildCodeBlock("HTML", "index.html", slot.html, "text/html"));
    card.appendChild(buildCodeBlock("CSS", "style.css", slot.css, "text/css"));
    return card;
  }

  function buildPreview(slot) {
    var wrapper = element("div", "preview");
    var bar = element("div", "preview-bar");
    var frame = element("iframe", "preview-frame");
    frame.setAttribute("sandbox", "");
    frame.setAttribute("title", "Live preview of screenshot " + slot.position);
    frame.srcdoc = slot.preview;

    [["Desktop", "100%"], ["Tablet", "768px"], ["Phone", "375px"]].forEach(function (size, index) {
      var button = element("button", "small-button" + (index === 0 ? " active" : ""), size[0]);
      button.type = "button";
      button.addEventListener("click", function () {
        frame.style.width = size[1];
        Array.prototype.forEach.call(bar.children, function (other) { other.classList.remove("active"); });
        button.classList.add("active");
      });
      bar.appendChild(button);
    });

    wrapper.appendChild(bar);
    wrapper.appendChild(frame);
    return wrapper;
  }

  function buildCodeBlock(label, filename, code, mime) {
    var block = element("div", "code-block");
    var bar = element("div", "code-bar");
    bar.appendChild(element("h4", "code-label", label));

    var copy = element("button", "small-button", "Copy");
    copy.type = "button";
    copy.addEventListener("click", function () { copyText(code, copy); });

    var download = element("button", "small-button", "Download");
    download.type = "button";
    download.addEventListener("click", function () { downloadText(filename, code, mime); });

    bar.appendChild(copy);
    bar.appendChild(download);
    block.appendChild(bar);

    var pre = element("pre", "code-text");
    pre.appendChild(element("code", "", code));
    pre.tabIndex = 0;
    block.appendChild(pre);
    return block;
  }

  function copyText(text, button) {
    var done = function () {
      button.textContent = "Copied!";
      setTimeout(function () { button.textContent = "Copy"; }, 1500);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done);
      return;
    }
    var area = element("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    document.body.removeChild(area);
    done();
  }

  function downloadText(filename, text, mime) {
    var link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: mime + ";charset=utf-8" }));
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // --- Kept batches list ---
  document.querySelectorAll("[data-delete-batch]").forEach(function (button) {
    button.addEventListener("click", function () {
      var batchId = button.dataset.deleteBatch;
      if (!window.confirm("Delete this batch, its pictures and its code?")) return;
      fetch(urlFor(tool.dataset.deleteUrlTemplate, batchId), { method: "POST", headers: { "X-CSRFToken": csrf } })
        .then(function () { button.closest("li").remove(); });
    });
  });

  // --- Open a kept batch from the list ---
  if (tool.dataset.openBatch) beginWatching(tool.dataset.openBatch);
})();
