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