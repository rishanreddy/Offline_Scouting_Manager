// Drag-and-drop for scouting fields using SortableJS
// Requires: static/vendor/sortable.min.js

document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("fieldsContainer");
  if (!container || typeof Sortable === "undefined") return;

  Sortable.create(container, {
    animation: 180,
    handle: ".field-row", // Drag anywhere on the row
    ghostClass: "sortable-ghost",
    chosenClass: "sortable-chosen",
    dragClass: "sortable-drag",
    filter: ".field-row-disabled",
    onEnd: function (evt) {
      // Optionally, you can renumber or update something here
    },
  });
});
