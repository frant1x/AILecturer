document.addEventListener("DOMContentLoaded", function () {
    const departmentCards = document.querySelectorAll(".card-hover-svg");
    const courseSection = document.getElementById("course_choice");
    const courseCards = document.querySelectorAll("#course_choice .col");
    const noCoursesMessage = document.getElementById("no-courses-message");

    let activeCard = null;

    courseSection.style.display = "none";
    noCoursesMessage.style.display = "none";

    departmentCards.forEach(card => {
        card.addEventListener("click", function () {
            if (activeCard === this) {
                this.classList.remove("active");
                activeCard = null;
                courseSection.style.display = "none";
                noCoursesMessage.style.display = "none";
                return;
            }

            departmentCards.forEach(c => c.classList.remove("active"));
            this.classList.add("active");
            activeCard = this;

            const deptName = this.querySelector("h5").innerText.trim();

            // Фільтрація курсів
            let visibleCount = 0;
            courseCards.forEach(courseCard => {
                const courseData = courseCard.dataset.department;
                if (courseData === deptName) {
                    courseCard.style.display = "block";
                    visibleCount++;
                } else {
                    courseCard.style.display = "none";
                }
            });

            if (visibleCount > 0) {
                courseSection.style.display = "block";
                noCoursesMessage.style.display = "none";
            } else {
                courseSection.style.display = "none";
                noCoursesMessage.style.display = "block";
            }

            if (visibleCount > 0) {
                courseSection.scrollIntoView({ behavior: "smooth", block: "start" });
            } else {
                noCoursesMessage.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const resourceLinks = document.querySelectorAll('.resource-link');
    const iconElems = document.querySelectorAll('.file-icon');

    resourceLinks.forEach((link, index) => {
        let url = link.getAttribute('href').replace(/\\/g, '/');
        const iconElem = iconElems[index]; // відповідна іконка

        const ext = url.split('.').pop().toLowerCase();

        let iconClass = 'bi-file-earmark-text';

        const iconMap = {
            pdf: 'bi-file-earmark-pdf',
            doc: 'bi-file-earmark-word',
            docx: 'bi-file-earmark-word',
            xls: 'bi-file-earmark-excel',
            xlsx: 'bi-file-earmark-excel',
            png: 'bi-file-earmark-image',
            jpg: 'bi-file-earmark-image',
            jpeg: 'bi-file-earmark-image',
            gif: 'bi-file-earmark-image',
            zip: 'bi-file-earmark-zip',
            rar: 'bi-file-earmark-zip',
            '7z': 'bi-file-earmark-zip'
        };

        if (ext in iconMap) {
            iconClass = iconMap[ext];
        }

        iconElem.classList.add('bi', iconClass);
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const input = document.getElementById("course-search");
    const resultsBox = document.getElementById("search-results");

    input.addEventListener("input", function () {
      const query = input.value;

      if (query.length < 2) {
        resultsBox.innerHTML = "";
        return;
      }

      fetch(`${autocompleteUrl}?q=${encodeURIComponent(query)}`)
        .then((response) => response.json())
        .then((data) => {
          resultsBox.innerHTML = "";
          if (data.results.length === 0) {
            resultsBox.style.display = "none";
            return;
          }
          resultsBox.style.display = "block";
          data.results.forEach((course) => {
            const item = document.createElement("a");
            item.classList.add("list-group-item", "list-group-item-action");
            item.href = courseUrlTemplate.replace("__ID__", course.id);
            item.textContent = course.name;
            resultsBox.appendChild(item);
          });
        });
    });

    document.addEventListener("click", function (e) {
      if (!input.contains(e.target) && !resultsBox.contains(e.target)) {
        resultsBox.innerHTML = "";
        resultsBox.style.display = "none";
      }
    });
  });


$(function(){
    $(".active-chat").niceScroll();
}) 

const textarea = document.getElementById('chat-input');
const maxRows = 6;
const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight);

textarea.style.height = lineHeight + 'px'; // початкова висота - 1 рядок

textarea.addEventListener('input', () => {
  textarea.style.height = 'auto'; // скидати висоту для правильного scrollHeight

  // Обчислюємо максимальну висоту для 6 рядків
  const maxHeight = lineHeight * maxRows;

  if (textarea.scrollHeight > maxHeight) {
    // Якщо текст більше 6 рядків, фіксуємо висоту і додаємо прокрутку
    textarea.style.height = maxHeight + 'px';
    textarea.style.overflowY = 'auto';
  } else {
    // Інакше автоматично підлаштовуємо висоту і ховаємо прокрутку
    textarea.style.height = textarea.scrollHeight + 'px';
    textarea.style.overflowY = 'hidden';
  }
});

async function sendMessage(event) {
    event.preventDefault();
    const textarea = document.getElementById('chat-input');
    const message = textarea.value.trim();
    if (!message) return;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const chatBody = document.getElementById('chat-body');
    const courseId = chatBody.dataset.courseId;
    const sessionId = chatBody.dataset.sessionId;

    if (!sessionId) {
        alert('Виберіть або створіть сесію чату!');
        return;
    }

    const chatMessages = document.getElementById('messages');

    const avatarUrl = chatMessages.dataset.avatarUrl;
    chatMessages.insertAdjacentHTML('beforeend', `
        <div class="message user">
            <div class="avatar">
                <img src="${avatarUrl}" alt="">
            </div>
            <div class="text">${message}</div>
        </div>
    `);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    textarea.value = '';
    textarea.disabled = true;

    try {
        const response = await fetch(`/courses/${courseId}/ai_chat/${sessionId}/get_answer/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({ content: message })
        });

        if (!response.ok) {
            throw new Error('Помилка сервера');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let botMessageElem = null;
        let botMessageContentRaw = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            let parts = buffer.split("\n\n");
            buffer = parts.pop();

            for (let part of parts) {
                const line = part.trim();
                if (!line.startsWith("data:")) continue;

                const jsonStr = line.replace("data: ", "").trim();
                if (jsonStr === "[DONE]") {
                    textarea.disabled = false;
                    textarea.focus();
                    return;
                }

                try {
                    const data = JSON.parse(jsonStr);
                    if (!botMessageElem) {
                        chatMessages.insertAdjacentHTML('beforeend', `
                            <div class="message bot">
                                <div class="avatar">
                                    <img src="/static/img/bot.png" alt="">
                                </div>
                                <div class="text"></div>
                            </div>
                        `);
                        botMessageElem = chatMessages.querySelector(".message.bot:last-child .text");
                    }
                    botMessageContentRaw += data.partial;

                    const html = marked.parse(botMessageContentRaw);

                    botMessageElem.innerHTML = html;

                    if (window.MathJax) {
                        MathJax.typesetPromise([botMessageElem]).catch(function (err) {
                            console.error("MathJax typeset failed: ", err);
                        });
                    }

                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } catch (e) {
                    console.error("JSON parse error:", e, "raw data:", jsonStr);
                }
            }
        }

        textarea.disabled = false;
        textarea.focus();

    } catch (error) {
        alert(error.message);
        textarea.disabled = false;
        textarea.focus();
    }
}