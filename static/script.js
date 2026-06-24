const openAddFormButton = document.querySelector("#open-add-form");
const closeAddFormButton = document.querySelector("#close-add-form");
const addTaskOverlay = document.querySelector("#add-task-overlay");
const addTaskForm = document.querySelector("#add-task-form");
const addTaskMessage = document.querySelector("#add-task-message");

function openAddForm() {
    addTaskOverlay.classList.remove("hidden");
}

function closeAddForm() {
    addTaskOverlay.classList.add("hidden");
    addTaskMessage.textContent = "";
}

openAddFormButton.addEventListener("click", openAddForm);
closeAddFormButton.addEventListener("click", closeAddForm);

addTaskOverlay.addEventListener("click", (event) => {
    if (event.target === addTaskOverlay) {
        closeAddForm();
    }
});

addTaskForm.addEventListener("htmx:afterRequest", (event) => {
    if (!event.detail.successful) {
        addTaskMessage.textContent = "Impossible de créer la task.";
        return;
    }

    addTaskForm.reset();
    closeAddForm();
});
