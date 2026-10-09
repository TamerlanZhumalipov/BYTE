import React, { useState } from "react";
import { useByte, PostForm } from "../core";
export default function Header() {
  const { t, user, language, routes, path, logo, page } = useByte();
  const [menu, setMenu] = useState(false);
  const [light, setLight] = useState(() =>
    document.documentElement.classList.contains("light-theme"),
  );
  const publicPage = ["index", "login"].includes(page);
  function theme() {
    const next = !light;
    setLight(next);
    document.documentElement.classList.toggle("light-theme", next);
    try {
      localStorage.setItem("byte-theme", next ? "light" : "dark");
    } catch {}
  }
  const links = publicPage
    ? [
        ["Языки", routes.index + "#tracks"],
        ["ҰБТ", routes.index + "#ent"],
        ["Контесты", routes.index + "#contests"],
        ["Пакеты", routes.index + "#pricing"],
        ["Вопросы", routes.index + "#faq"],
        [
          user ? "Личный кабинет" : "Оставить заявку",
          user ? routes.dashboard : routes.index + "#cta",
        ],
      ]
    : [
        ["Материалы", routes.dashboard],
        ["Аналитика", routes.analytics],
        ["Лайв-контест", routes.contest],
      ];
  return (
    <header className="react-header">
      <div className="react-header-inner">
        <a className="brand" href={routes.index}>
          <img src={logo} alt="" />
          BYTE
        </a>
        <button
          className="btn btn-ghost react-menu-toggle"
          type="button"
          aria-label={t("Меню", "Мәзір")}
          aria-expanded={menu}
          aria-controls="main-nav"
          onClick={() => setMenu(!menu)}
        >
          ☰
        </button>
        <nav
          id="main-nav"
          className={`react-nav ${menu ? "is-open" : ""}`}
          aria-label={t("Разделы", "Бөлімдер")}
        >
          {links.map(([text, url]) => (
            <a
              key={url}
              href={url}
              aria-current={path === url ? "page" : undefined}
              className={path === url ? "is-active" : ""}
            >
              {t(text)}
            </a>
          ))}
        </nav>
        <div className="react-header-actions">
          {user && <span className="app-user-name">{user.username}</span>}
          <PostForm
            action={routes.set_language}
            className="lang-switch"
            aria-label={t("Язык", "Тіл")}
          >
            <input type="hidden" name="next" value={path} />
            {[
              ["ru", "RU"],
              ["kk", "KZ"],
            ].map(([lang, label]) => (
              <button
                key={lang}
                className={`lang-option ${language === lang ? "is-active" : ""}`}
                name="language"
                value={lang}
                type="submit"
                aria-label={label}
              >
                {label}
              </button>
            ))}
          </PostForm>
          <button
            className="theme-button"
            type="button"
            aria-label={t(light ? "Тёмная тема" : "Светлая тема")}
            onClick={theme}
          >
            {light ? "☾" : "☀"}
          </button>
          {user ? (
            <PostForm action={routes.logout}>
              <button className="btn btn-ghost btn-sm" type="submit">
                {t("Выйти")}
              </button>
            </PostForm>
          ) : (
            <a className="btn btn-ghost btn-sm" href={routes.login}>
              {t("Войти")}
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
