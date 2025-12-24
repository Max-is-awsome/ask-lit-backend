// the contents of this file was written with the help of generative AI

async function sendMessage() {
    const userInput = document.getElementById("userInput").value;
    const responseElement = document.getElementById("response");
    const bookList = document.getElementById("bookList");

    responseElement.innerText = "Thinking...";
    bookList.innerHTML = ""; // Clear previous results

    try {
        const response = await fetch("http://127.0.0.1:5001/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userInput })
        });

        const data = await response.json();

        if (response.ok) {
            responseElement.innerText = data.reply;

            if (data.books && data.books.length > 0) {
                data.books.forEach(book => {
                    const li = document.createElement("li");
                    li.innerHTML = `<strong>${book.title}</strong> (${book.published_date})<br>
                                    "${book.quote}"<br>
                                    <a href="${book.link}" target="_blank">Preview</a>`;
                    bookList.appendChild(li);
                });
            } else {
                bookList.innerHTML = "<li>No books found.</li>";
            }
        } else {
            responseElement.innerText = "Error: " + (data.error || "Unknown error.");
        }
    } catch (error) {
        responseElement.innerText = "Error: Unable to connect to the server.";
    }
}
