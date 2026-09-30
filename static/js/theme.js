document.addEventListener("DOMContentLoaded", () => {

    const html = document.documentElement;
    const button = document.getElementById("themeButton");

    if (!button) {
        return;
    }


    /* Загружаем сохранённую тему */

    const savedTheme =
        localStorage.getItem("byte-theme") || "dark";

    applyTheme(savedTheme);


    /* Переключение */

    button.addEventListener("click", () => {

        const currentTheme =
            html.classList.contains("light-theme")
                ? "light"
                : "dark";

        const newTheme =
            currentTheme === "dark"
                ? "light"
                : "dark";

        applyTheme(newTheme);

        localStorage.setItem(
            "byte-theme",
            newTheme
        );
    });


    function applyTheme(theme) {

        html.classList.remove(
            "light-theme",
            "dark-theme"
        );

        html.classList.add(
            `${theme}-theme`
        );

        button.textContent =
            theme === "light"
                ? "☾"
                : "☀";
    }

});