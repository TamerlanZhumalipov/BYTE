import React from "react";
import { useByte, PostForm, number } from "../core";
export default function Quiz() {
  const { t, props: p, routes, path } = useByte();
  const r = p.result;
  return (
    <main className="quiz-page">
      <div className="quiz-shell">
        <nav className="crumbs">
          <a href={routes.dashboard}>{t("Материалы")}</a>
          <span>/</span>
          <a href={p.topic.url}>{p.topic.title}</a>
          <span>/ {t("Проверочный тест")}</span>
        </nav>
        <header className="quiz-hero">
          <div>
            <span className="kicker">{t("закрепление основной темы")}</span>
            <h1>{p.topic.title}</h1>
            <p>
              {t("Проходной результат", "Өту шегі")}: {p.pass_percent}%
            </p>
          </div>
          {p.best_score !== null && (
            <div className="quiz-best">
              <span>{t("Лучший результат")}</span>
              <strong>{p.best_score}%</strong>
            </div>
          )}
        </header>
        {r ? (
          <>
            <section
              className={`quiz-result ${r.passed ? "is-passed" : "is-failed"}`}
            >
              <div className="quiz-result-score">
                <span>{t(r.passed ? "Тема пройдена" : "Нужно повторить")}</span>
                <strong>{r.score}%</strong>
                <small>
                  {r.correct_count} / {r.total}
                </small>
              </div>
              <div>
                <h2>
                  {t(
                    r.passed
                      ? "Тема пройдена"
                      : "До проходного результата не хватило",
                  )}
                </h2>
                <p>
                  {t(
                    "Результат сохранён в аналитике. Можно продолжать обучение или пройти тест ещё раз, чтобы улучшить процент.",
                  )}
                </p>
                <div className="quiz-actions">
                  {r.next && (
                    <a className="btn btn-primary" href={r.next.url}>
                      {t("Перейти к следующей теме →")}
                    </a>
                  )}
                  <a className="btn btn-ghost" href={path}>
                    {t("Пройти тест снова")}
                  </a>
                  <a className="btn btn-ghost" href={routes.analytics}>
                    {t("Посмотреть аналитику")}
                  </a>
                </div>
              </div>
            </section>
            <section className="quiz-review">
              <h2>{t("Разбор попытки")}</h2>
              <div className="quiz-review-list">
                {r.review.map((item, i) => (
                  <article
                    key={i}
                    className={`review-card ${item.is_correct ? "is-correct" : "is-wrong"}`}
                  >
                    <span>{number(i + 1)}</span>
                    <div>
                      <h3>{item.question}</h3>
                      <p>
                        {t("Ваш ответ")}: {item.selected || t("не выбран")}
                      </p>
                      {!item.is_correct && item.correct && (
                        <p className="correct-answer">
                          {t("Правильный ответ")}: {item.correct}
                        </p>
                      )}
                    </div>
                    <span>{item.is_correct ? "✓" : "×"}</span>
                  </article>
                ))}
              </div>
            </section>
          </>
        ) : p.questions.length ? (
          <PostForm className="quiz-form" action={path}>
            {p.questions.map((q, i) => (
              <fieldset className="quiz-question" key={q.id}>
                <legend>
                  <span>{number(i + 1)}</span>
                  {q.text}
                </legend>
                <div className="quiz-options">
                  {q.choices.map((a) => (
                    <label className="quiz-option" key={a.id}>
                      <input
                        type="radio"
                        name={`q_${q.id}`}
                        value={a.id}
                        required
                      />
                      <span className="quiz-radio" aria-hidden="true" />
                      <span>{a.text}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <div className="quiz-submit-bar">
              <span>
                {p.questions.length} {t("вопросов", "сұрақ")}
              </span>
              <button className="btn btn-primary" type="submit">
                {t("Завершить тест", "Тестті аяқтау")}
              </button>
            </div>
          </PostForm>
        ) : (
          <p className="doc-empty">{t("В тесте пока нет вопросов.")}</p>
        )}
      </div>
    </main>
  );
}
