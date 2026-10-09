import React from "react";
import { useByte, dateTime, number } from "../core";
import Forecast from "../components/Forecast";
export default function Analytics() {
  const { t, props: p, routes, language } = useByte();
  return (
    <main className="analytics-page">
      <div className="analytics-shell">
        <header className="analytics-head">
          <div>
            <span className="kicker">{t("ваш прогресс")}</span>
            <h1>{t("Аналитика обучения")}</h1>
            <p>{t("Результаты обучения и оценка готовности к ЕНТ сегодня.")}</p>
          </div>
          <a className="btn btn-ghost" href={routes.dashboard}>
            {t("Продолжить обучение")}
          </a>
        </header>
        <section className="analytics-kpis">
          <article className="analytics-card">
            <span>{t("Пройдено тем")}</span>
            <strong>
              {p.completed_topics} / {p.total_topics}
            </strong>
            <div className="analytics-progress">
              <i style={{ width: `${p.progress_percent}%` }} />
            </div>
            <small>
              {p.progress_percent}% {t("программы")}
            </small>
          </article>
          <article className="analytics-card">
            <span>{t("Средний лучший результат")}</span>
            <strong>
              {p.average_score === null ? "—" : `${p.average_score}%`}
            </strong>
            <small>{t("по темам, где уже были попытки")}</small>
          </article>
          <article className="analytics-card">
            <span>{t("Темы ЕНТ с результатами")}</span>
            <strong>
              {p.forecast.assessed_topics ?? 0} / {p.forecast.topic_count ?? 0}
            </strong>
            <small>{t("по связанным тестам и контестам")}</small>
          </article>
        </section>
        <Forecast data={p.forecast} />
        <section className="analytics-section">
          <h2>{t("Результаты по темам")}</h2>
          <p>
            {t(
              "Следующая тема открывается только после успешного теста предыдущей.",
            )}
          </p>
          <div className="analytics-table-wrap">
            <table className="analytics-table">
              <thead>
                <tr>
                  {[
                    "Тема",
                    "Статус",
                    "Лучший результат",
                    "Попыток",
                    "Последняя попытка",
                  ].map((s) => (
                    <th key={s}>{t(s)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {p.rows.map((row, i) => (
                  <tr
                    key={row.topic.id}
                    className={row.locked ? "is-locked" : ""}
                  >
                    <td>
                      <span className="analytics-topic-num">
                        {number(i + 1)}
                      </span>
                      <strong>{row.topic.title}</strong>
                    </td>
                    <td>
                      {t(
                        row.completed
                          ? "пройдено"
                          : row.locked
                            ? "закрыто"
                            : "в процессе",
                      )}
                    </td>
                    <td>
                      {row.best_score === null ? "—" : `${row.best_score}%`}
                    </td>
                    <td>{row.attempts_count}</td>
                    <td>{dateTime(row.latest?.created_at, language)}</td>
                  </tr>
                ))}
                {!p.rows.length && (
                  <tr>
                    <td colSpan="5">{t("Основные темы пока не добавлены.")}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
        <section className="analytics-section">
          <h2>{t("Последние попытки")}</h2>
          <div className="attempt-grid">
            {p.recent_attempts.map((a) => (
              <article className="attempt-card" key={a.id}>
                <div>
                  <span>{dateTime(a.created_at, language)}</span>
                  <h3>{a.topic.title}</h3>
                </div>
                <strong className={a.passed ? "is-good" : "is-bad"}>
                  {a.score}%
                </strong>
              </article>
            ))}
            {!p.recent_attempts.length && (
              <p>
                {t("Здесь появятся результаты после первой попытки теста.")}
              </p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
