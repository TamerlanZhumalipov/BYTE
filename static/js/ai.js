document.addEventListener("DOMContentLoaded", () => {

    const button = document.getElementById("byteAiButton");
    const windowElement = document.getElementById("byteAiWindow");
    const closeButton = document.getElementById("byteAiClose");

    const input = document.getElementById("byteAiInput");
    const sendButton = document.getElementById("byteAiSend");

    const messages = document.getElementById("byteAiMessages");


    /* =====================================================
       OPEN / CLOSE
       ===================================================== */

    function openAI() {
        windowElement.classList.add("is-open");

        setTimeout(() => {
            input.focus();
        }, 250);
    }

    function closeAI() {
        windowElement.classList.remove("is-open");
    }


    button.addEventListener("click", () => {

        if (windowElement.classList.contains("is-open")) {
            closeAI();
        } else {
            openAI();
        }

    });

    closeButton.addEventListener("click", closeAI);


    /* =====================================================
       ADD USER MESSAGE
       ===================================================== */

    function addUserMessage(text) {

        const message = document.createElement("div");

        message.className =
            "byte-ai-message byte-ai-message-user";

        message.textContent = text;

        messages.appendChild(message);

        scrollToBottom();
    }


    /* =====================================================
       ADD NORMAL BOT MESSAGE
       ===================================================== */

    function addBotMessage(text) {

        const message = document.createElement("div");

        message.className =
            "byte-ai-message byte-ai-message-bot";

        message.textContent = text;

        messages.appendChild(message);

        scrollToBottom();
    }


    /* =====================================================
       TYPE BOT MESSAGE
       ===================================================== */

    async function typeBotMessage(text) {

        const message = document.createElement("div");

        message.className =
            "byte-ai-message byte-ai-message-bot";

        messages.appendChild(message);


        /*
         * Разделяем текст на слова,
         * сохраняя пробелы и переносы строк.
         */

        const parts = text.match(/\S+|\s+/g) || [];


        const cursor = document.createElement("span");

        cursor.className = "byte-ai-typing-cursor";


        for (const part of parts) {

            message.appendChild(
                document.createTextNode(part)
            );

            message.appendChild(cursor);

            scrollToBottom();


            /*
             * Скорость печати.
             *
             * Пробелы появляются быстро,
             * слова немного медленнее.
             */

            if (/\s+/.test(part)) {

                await sleep(15);

            } else {

                await sleep(
                    Math.min(
                        55,
                        Math.max(
                            18,
                            part.length * 5
                        )
                    )
                );

            }

            /*
             * Убираем курсор перед добавлением
             * следующего слова.
             */

            if (cursor.parentNode === message) {
                message.removeChild(cursor);
            }
        }


        scrollToBottom();
    }


    /* =====================================================
       LOADING MESSAGE
       ===================================================== */

    function addLoadingMessage() {

        const loading = document.createElement("div");

        loading.className =
            "byte-ai-message byte-ai-message-bot";

        loading.innerHTML = `
            <span class="byte-ai-loading-dot">●</span>
            <span class="byte-ai-loading-dot">●</span>
            <span class="byte-ai-loading-dot">●</span>
        `;

        messages.appendChild(loading);

        scrollToBottom();

        return loading;
    }


    /* =====================================================
       CSRF
       ===================================================== */

    function getCSRFToken() {

        const meta =
            document.querySelector(
                'meta[name="csrf-token"]'
            );

        return meta
            ? meta.getAttribute("content")
            : "";
    }


    /* =====================================================
       SEND MESSAGE
       ===================================================== */

    async function sendMessage() {

        const text = input.value.trim();

        if (!text) return;


        addUserMessage(text);

        input.value = "";


        const loading = addLoadingMessage();


        /*
         * Блокируем кнопку на время запроса.
         */

        sendButton.disabled = true;
        input.disabled = true;


        try {

            const response = await fetch(
                "/api/ai/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken()
                    },

                    body: JSON.stringify({
                        question: text
                    })
                }
            );


            const data = await response.json();


            loading.remove();


            if (!response.ok || !data.ok) {

                addBotMessage(
                    data.error ||
                    "Не удалось получить ответ."
                );

                return;
            }


            /*
             * Вместо мгновенного вывода:
             *
             * addBotMessage(data.answer)
             *
             * используем красивую печать.
             */

            await typeBotMessage(data.answer);


        } catch (error) {

            loading.remove();

            addBotMessage(
                "Не удалось подключиться к AI. Попробуйте ещё раз."
            );

        } finally {

            sendButton.disabled = false;
            input.disabled = false;

            input.focus();
        }


        scrollToBottom();
    }


    /* =====================================================
       ENTER
       ===================================================== */

    sendButton.addEventListener(
        "click",
        sendMessage
    );


    input.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();
            }

        }
    );


    /* =====================================================
       HELPERS
       ===================================================== */

    function sleep(ms) {

        return new Promise(
            resolve => setTimeout(resolve, ms)
        );
    }


    function scrollToBottom() {

        messages.scrollTop =
            messages.scrollHeight;
    }

});