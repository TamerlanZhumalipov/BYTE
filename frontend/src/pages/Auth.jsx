import React from "react";
import { useByte, PostForm, dateTime } from "../core";
export default function Auth({ contest = false }) {
  const { t, props, language, routes } = useByte();
  const name = contest ? "login" : "username";
  return (
    <main className="auth-main">
      <div className="auth-card">
        <h1 className="auth-title">
          {t(contest ? "Вход в контест" : "С возвращением")}
        </h1>
        <p className="auth-subtitle">
          {t(
            contest
              ? "У контеста отдельные логин и пароль — не такие, как на сайте. Их выдаёт куратор."
              : "Войдите, чтобы продолжить обучение и записаться на ближайший контест.",
          )}
        </p>
        {props.next_contest && (
          <p>
            {t("Ближайший контест")}: {props.next_contest.title} ·{" "}
            {dateTime(props.next_contest.starts_at, language)}
          </p>
        )}
        {props.error && (
          <div role="alert" className="auth-error show">
            {contest
              ? props.error
              : t("Неверный email/логин или пароль. Попробуйте ещё раз.")}
          </div>
        )}
        <PostForm action={contest ? routes.contest_login : routes.login}>
          {!contest && (
            <input type="hidden" name="next" value={props.next || ""} />
          )}
          <div className="field-group">
            <label htmlFor={name}>
              {t(contest ? "Логин контеста" : "Email или логин")}
            </label>
            <input
              id={name}
              name={name}
              defaultValue={props.username || ""}
              autoComplete={contest ? "off" : "username"}
              autoCapitalize="none"
              required
            />
          </div>
          <div className="field-group">
            <label htmlFor="password">
              {t(contest ? "Пароль контеста" : "Пароль")}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={contest ? "off" : "current-password"}
              required
            />
          </div>
          <button className="btn btn-primary btn-block" type="submit">
            {t(contest ? "Войти в контест" : "Войти")}
          </button>
        </PostForm>
        {!contest && (
          <p className="auth-switch">
            <a href={routes.index + "#cta"}>{t("Оставить заявку")}</a>
          </p>
        )}
      </div>
    </main>
  );
}
