import React from "react";
import { useByte } from "../core";
export default function Forecast({ data: f }) {
  const { t, routes } = useByte();
  return (
    <section className="byte-forecast" aria-labelledby="forecast-heading">
      <header className="forecast-heading">
        <div>
          <span className="kicker">BYTE AI · FORECAST</span>
          <h2 id="forecast-heading">{t("Если сдавать ЕНТ сегодня")}</h2>
        </div>
        <span className="forecast-badge">{t("Предварительная модель")}</span>
      </header>
      {f.status === "unavailable" ? (
        <p>
          {t(
            "Спецификация ещё не настроена. Прогноз появится после настройки тем ЕНТ.",
          )}
        </p>
      ) : (
        <>
          <div className="forecast-overview">
            <div className="forecast-result">
              <div className="forecast-number">
                {f.score === null ? "—" : `≈ ${f.score}`}{" "}
                <span>/ {f.max_score}</span>
              </div>
              {f.score !== null ? (
                <>
                  <p>
                    {t("Ориентировочный диапазон")}:{" "}
                    <strong>
                      {f.low}–{f.high}
                    </strong>
                  </p>
                  <p>
                    {t("Надёжность данных")}:{" "}
                    <strong>
                      {t(f.confidence === "medium" ? "средняя" : "низкая")}
                    </strong>
                  </p>
                </>
              ) : (
                <>
                  <h3>{t("Пока недостаточно данных")}</h3>
                  <p>
                    {t(
                      "Пройдите тесты по нескольким темам. Один проверенный полный пробник тоже позволит построить первую оценку.",
                    )}
                  </p>
                </>
              )}
              <p>
                {t("Изменение за 30 дней")}:{" "}
                {f.delta === null ? (
                  t("данных пока мало")
                ) : (
                  <strong>
                    {f.delta > 0 ? "+" : ""}
                    {f.delta}
                  </strong>
                )}
              </p>
            </div>
            <div className="forecast-evidence">
              <h3>{t("На чём основан прогноз")}</h3>
              <dl>
                {[
                  ["Тесты по разным темам", f.quiz_count],
                  ["Связанные задачи контестов", f.contest_count],
                  ["Проверенные пробники", f.mock_count],
                ].map(([name, value]) => (
                  <div key={name}>
                    <dt>{t(name)}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
              <p>
                {t("Обеспеченность данными")}:{" "}
                <strong>{f.coverage_percent}%</strong>
              </p>
              <progress
                max="100"
                value={f.coverage_percent}
                aria-label={t("Обеспеченность данными")}
              />
              <small>
                {t(
                  "Учитываются давность, объём и покрытие результатов. Повтор одного теста не считается новой темой.",
                )}
              </small>
            </div>
          </div>
          <p className="forecast-disclaimer">
            {t(
              "Это предварительная оценка, а не гарантия результата. Диапазон модельный: его точность ещё предстоит проверить на реальных экзаменах.",
            )}
          </p>
          <div className="forecast-next">
            <h3>{t("Что улучшить дальше")}</h3>
            <div className="forecast-recommendations">
              {f.recommendations.map((topic) => (
                <article key={topic.id}>
                  <span>{topic.code}</span>
                  <h4>{topic.title}</h4>
                  <p>
                    {t(
                      !topic.mapped && !topic.has_evidence
                        ? "Материалов по теме пока нет. Обсудите диагностику с куратором."
                        : !topic.has_evidence
                          ? "Нужна диагностика: данных по теме пока нет."
                          : "Повторите тему и проверьте результат новым тестом или пробником.",
                    )}
                  </p>
                </article>
              ))}
            </div>
            <a className="btn btn-ghost" href={routes.dashboard}>
              {t("Продолжить обучение")} →
            </a>
          </div>
          <details className="forecast-details">
            <summary>
              {t("Разбор по темам ЕНТ")} · {f.topic_count}
            </summary>
            <p>
              {t(
                "Освоение — оценка по доступным результатам. Вклад в баллы рассчитан по весам модели; это не официальное распределение заданий ЕНТ.",
              )}
            </p>
            <div className="analytics-table-wrap">
              <table className="analytics-table forecast-table">
                <thead>
                  <tr>
                    {["Тема", "Освоение", "Вклад модели", "Данные"].map(
                      (label) => (
                        <th key={label}>{t(label)}</th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {f.topics.map((topic) => (
                    <tr key={topic.id}>
                      <td>
                        <span className="analytics-topic-num">
                          {topic.code}
                        </span>
                        <strong>{topic.title}</strong>
                      </td>
                      <td>
                        {topic.mastery === null ? "—" : `${topic.mastery}%`}
                      </td>
                      <td>
                        {topic.has_evidence
                          ? `${topic.model_points} / ${topic.model_max}`
                          : "—"}
                      </td>
                      <td>
                        {topic.has_evidence
                          ? `${t("Тесты")}: ${topic.quiz_roots} · ${t("Контесты")}: ${topic.contest_tasks}`
                          : t("Нет результатов")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <details className="forecast-details">
            <summary>{t("Динамика за 30 дней")}</summary>
            <p>
              {t(
                "История пересчитана по текущим связям и весам. Для каждой даты используются только результаты, полученные к тому моменту.",
              )}
            </p>
            <ol className="forecast-history">
              {f.history.map((point) => (
                <li key={point.date}>
                  <time>{point.date}</time>
                  <progress
                    max={f.max_score}
                    value={point.score ?? 0}
                    aria-label={point.date}
                  />
                  <strong>{point.score ?? "—"}</strong>
                </li>
              ))}
            </ol>
          </details>
          <details className="forecast-details">
            <summary>{t("Как считается прогноз")}</summary>
            {[
              "Свежие результаты влияют сильнее старых. Для каждого теста учитываются последние три попытки; повторения не увеличивают объём независимых данных. Контесты дают дополнительный сигнал, а проверенные полные пробники имеют наибольший вес.",
              "По неизвестным темам модель использует нейтральное допущение 50% с широким диапазоном неопределённости. Это не означает, что тема освоена. При недостатке данных общий балл скрыт.",
              "Чтение материалов и прохождение курса сами по себе не добавляют баллы. Широкая связь раздела с темой ЕНТ может покрывать её лишь частично.",
              f.equal_weights
                ? "Все темы имеют одинаковый модельный вес: официальная спецификация не задаёт баллы каждой темы."
                : "Используются веса, заданные куратором. Они являются допущением модели.",
              "Пробники уточняют общий балл; без ответов по темам они не изменяют разбор освоения тем.",
            ].map((text) => (
              <p key={text}>{t(text)}</p>
            ))}
            {f.weight_note && <p>{f.weight_note}</p>}
          </details>
        </>
      )}
    </section>
  );
}
