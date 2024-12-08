async function sendQuestion() {
    const userInput = document.getElementById("user-input");
    const question = userInput.value;
    if (!question) return;
  
    // Mostrar pregunta en la interfaz
    const chatBox = document.getElementById("chat-box");
    const userMessage = document.createElement("div");
    userMessage.textContent = "Tú: " + question;
    chatBox.appendChild(userMessage);
  
    // Enviar pregunta al backend
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
  
    // Mostrar respuesta
    const botMessage = document.createElement("div");
    botMessage.textContent = "Bot: " + (data.answer || "Error al responder");
    chatBox.appendChild(botMessage);
  
    userInput.value = "";
  }
  
  document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("file-input");
    const files = fileInput.files; // Obtener todos los archivos seleccionados
    if (files.length === 0) {
        alert("Por favor selecciona al menos un archivo.");
        return;
    }

    const formData = new FormData();
    for (let file of files) {
        formData.append("files", file); // Añadir cada archivo al FormData
    }

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();

        if (response.ok) {
            alert(data.message || "Archivos subidos correctamente");
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error("Error al subir los archivos:", error);
        alert("Ocurrió un error al subir los archivos.");
    }
});

  