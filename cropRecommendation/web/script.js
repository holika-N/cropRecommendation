//comfirming value in nutreients section is a num
document.getElementById("nutrientForm").addEventListener("submit", function(event) {
    const input = document.getElementById("nitrogen");
    const val = input.valueAsNumber;

    if (!Number.isInteger(vlaue) || val < 0) {
        event.preventDefault();
        document.getElementById("error").textContent = 
            "Please enter a non-negative integer.";
    }
});

// Add to script.js
// Updates the summary tiles on the right as each dropdown changes.

["soil_ph", "K", "P", "Mg", "C"].forEach((id) => {
  const select = document.getElementById(id);
  const tile = document.getElementById("tile-" + id);
  if (!select || !tile) return;

  select.addEventListener("change", () => {
    tile.textContent = select.value || "–";
  });
});