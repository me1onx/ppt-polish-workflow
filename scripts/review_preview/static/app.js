(function () {
  "use strict";

  var slideListEl = document.getElementById("slide-list");
  var statusEl = document.getElementById("status");
  var counterEl = document.getElementById("nav-counter");
  var prevBtn = document.getElementById("nav-prev");
  var nextBtn = document.getElementById("nav-next");
  var saveBtn = document.getElementById("btn-save");
  var exitBtn = document.getElementById("btn-exit");
  var addBtn = document.getElementById("btn-add");
  var clearRegionBtn = document.getElementById("btn-clear-region");
  var annotationText = document.getElementById("annotation-text");
  var annotationListEl = document.getElementById("annotation-list");
  var slideWrap = document.getElementById("slide-wrap");
  var slideImage = document.getElementById("slide-image");
  var regionLayer = document.getElementById("region-layer");
  var emptyState = document.getElementById("empty-state");
  var targetText = document.getElementById("target-text");

  var slides = [];
  var currentSlide = null;
  var currentAnnotations = [];
  var selectedRegion = null;
  var draftRect = null;
  var dragStart = null;

  function api(path, options) {
    return fetch(path, options || {}).then(function (res) {
      if (!res.ok) {
        return res.json().catch(function () { return {}; }).then(function (body) {
          throw new Error(body.error || res.statusText);
        });
      }
      return res.json();
    });
  }

  function setStatus(message) {
    statusEl.textContent = message;
  }

  function slideIndex() {
    if (!currentSlide) return -1;
    return slides.findIndex(function (slide) { return slide.name === currentSlide; });
  }

  function updateNav() {
    var idx = slideIndex();
    counterEl.textContent = idx >= 0 ? (idx + 1) + " / " + slides.length : "— / —";
    prevBtn.disabled = idx <= 0;
    nextBtn.disabled = idx < 0 || idx >= slides.length - 1;
  }

  function renderSlideList() {
    slideListEl.innerHTML = "";
    slides.forEach(function (slide) {
      var item = document.createElement("button");
      item.className = "slide-item" + (slide.name === currentSlide ? " active" : "");
      item.dataset.name = slide.name;
      item.innerHTML = "<div>" + escapeHtml(slide.name) + "</div>" +
        "<div class=\"slide-meta\">" + slide.annotation_count + " annotation(s)</div>";
      item.addEventListener("click", function () { selectSlide(slide.name); });
      slideListEl.appendChild(item);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderRegions() {
    regionLayer.querySelectorAll(".saved-region").forEach(function (el) { el.remove(); });
    currentAnnotations.forEach(function (ann) {
      var target = ann.target || {};
      if (target.type !== "region") return;
      var rect = document.createElement("div");
      rect.className = "saved-region";
      rect.style.left = (target.x * 100) + "%";
      rect.style.top = (target.y * 100) + "%";
      rect.style.width = (target.width * 100) + "%";
      rect.style.height = (target.height * 100) + "%";
      regionLayer.appendChild(rect);
    });
  }

  function renderAnnotations() {
    annotationListEl.innerHTML = "";
    if (!currentAnnotations.length) {
      var empty = document.createElement("div");
      empty.className = "slide-meta";
      empty.textContent = "No annotations yet";
      annotationListEl.appendChild(empty);
      renderRegions();
      return;
    }
    currentAnnotations.forEach(function (ann) {
      var card = document.createElement("div");
      card.className = "annotation-card";
      var meta = document.createElement("div");
      meta.className = "slide-meta";
      meta.textContent = ann.target && ann.target.type === "region" ? "Region" : "Whole slide";
      var text = document.createElement("p");
      text.textContent = ann.annotation;
      var del = document.createElement("button");
      del.textContent = "Delete";
      del.addEventListener("click", function () { deleteAnnotation(ann.id); });
      card.appendChild(meta);
      card.appendChild(text);
      card.appendChild(del);
      annotationListEl.appendChild(card);
    });
    renderRegions();
  }

  function setSelectedRegion(region) {
    selectedRegion = region;
    targetText.textContent = region
      ? "Region: x " + Math.round(region.x * 100) + "%, y " + Math.round(region.y * 100) + "%"
      : "Whole slide";
  }

  function clearDraftRect() {
    if (draftRect) {
      draftRect.remove();
      draftRect = null;
    }
  }

  function selectSlide(name) {
    currentSlide = name;
    setSelectedRegion(null);
    clearDraftRect();
    api("/api/slide/" + encodeURIComponent(name)).then(function (data) {
      currentAnnotations = data.annotations || [];
      slideImage.src = data.image_url;
      slideWrap.classList.add("visible");
      emptyState.style.display = "none";
      setStatus("Previewing " + name);
      renderSlideList();
      renderAnnotations();
      updateNav();
    }).catch(function (err) {
      setStatus("Failed to load slide: " + err.message);
    });
  }

  function loadSlides(keepCurrent) {
    api("/api/slides").then(function (data) {
      slides = data.slides || [];
      if (!slides.length) {
        setStatus("No slides found");
        renderSlideList();
        updateNav();
        return;
      }
      var target = keepCurrent && currentSlide ? currentSlide : slides[0].name;
      renderSlideList();
      selectSlide(target);
    }).catch(function (err) {
      setStatus("Failed to load slides: " + err.message);
    });
  }

  function addAnnotation() {
    if (!currentSlide) return;
    var text = annotationText.value.trim();
    if (!text) {
      setStatus("Write an annotation first");
      return;
    }
    addBtn.disabled = true;
    api("/api/slide/" + encodeURIComponent(currentSlide) + "/annotate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        annotation: text,
        target: selectedRegion || { type: "slide" }
      })
    }).then(function () {
      annotationText.value = "";
      setSelectedRegion(null);
      clearDraftRect();
      loadSlides(true);
      setStatus("Annotation added");
    }).catch(function (err) {
      setStatus("Failed to add annotation: " + err.message);
    }).finally(function () {
      addBtn.disabled = false;
    });
  }

  function deleteAnnotation(id) {
    if (!currentSlide || !id) return;
    api("/api/slide/" + encodeURIComponent(currentSlide) + "/annotate/" + encodeURIComponent(id), {
      method: "DELETE"
    }).then(function () {
      loadSlides(true);
      setStatus("Annotation deleted");
    }).catch(function (err) {
      setStatus("Failed to delete annotation: " + err.message);
    });
  }

  function saveAll() {
    saveBtn.disabled = true;
    api("/api/save-all", { method: "POST" }).then(function (data) {
      setStatus("Saved " + data.annotations_count + " annotation(s): " + data.path);
    }).catch(function (err) {
      setStatus("Save failed: " + err.message);
    }).finally(function () {
      saveBtn.disabled = false;
    });
  }

  function exitPreview() {
    api("/api/shutdown", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "user-exit" })
    }).then(function () {
      setStatus("Preview stopped. You can close this tab.");
    }).catch(function (err) {
      setStatus("Shutdown failed: " + err.message);
    });
  }

  function layerPoint(event) {
    var rect = regionLayer.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))
    };
  }

  regionLayer.addEventListener("mousedown", function (event) {
    if (!currentSlide) return;
    dragStart = layerPoint(event);
    clearDraftRect();
    draftRect = document.createElement("div");
    draftRect.className = "region-rect";
    regionLayer.appendChild(draftRect);
  });

  window.addEventListener("mousemove", function (event) {
    if (!dragStart || !draftRect) return;
    var point = layerPoint(event);
    var x = Math.min(dragStart.x, point.x);
    var y = Math.min(dragStart.y, point.y);
    var width = Math.abs(point.x - dragStart.x);
    var height = Math.abs(point.y - dragStart.y);
    draftRect.style.left = (x * 100) + "%";
    draftRect.style.top = (y * 100) + "%";
    draftRect.style.width = (width * 100) + "%";
    draftRect.style.height = (height * 100) + "%";
  });

  window.addEventListener("mouseup", function (event) {
    if (!dragStart || !draftRect) return;
    var point = layerPoint(event);
    var x = Math.min(dragStart.x, point.x);
    var y = Math.min(dragStart.y, point.y);
    var width = Math.abs(point.x - dragStart.x);
    var height = Math.abs(point.y - dragStart.y);
    dragStart = null;
    if (width < 0.01 || height < 0.01) {
      clearDraftRect();
      setSelectedRegion(null);
      return;
    }
    setSelectedRegion({ type: "region", x: x, y: y, width: width, height: height });
  });

  prevBtn.addEventListener("click", function () {
    var idx = slideIndex();
    if (idx > 0) selectSlide(slides[idx - 1].name);
  });

  nextBtn.addEventListener("click", function () {
    var idx = slideIndex();
    if (idx >= 0 && idx < slides.length - 1) selectSlide(slides[idx + 1].name);
  });

  addBtn.addEventListener("click", addAnnotation);
  saveBtn.addEventListener("click", saveAll);
  exitBtn.addEventListener("click", exitPreview);
  clearRegionBtn.addEventListener("click", function () {
    clearDraftRect();
    setSelectedRegion(null);
  });

  api("/api/config").then(function () {
    loadSlides(false);
  }).catch(function (err) {
    setStatus("Preview unavailable: " + err.message);
  });
})();
