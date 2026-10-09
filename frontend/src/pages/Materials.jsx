import React, { useState } from "react";
import { useByte, RichText, externalURL, dateTime, number } from "../core";
import Assistant from "../components/Assistant";
function Tree({ nodes, depth = 0 }) {
  const { t, props } = useByte();
  return (
    <ul className={`tree-list ${depth ? "tree-sub" : ""}`}>
      {nodes.map((node) => (
        <li key={node.id}>
          {node.locked ? (
            <div className="tree-link is-locked" aria-disabled="true">
              🔒 {node.title}
            </div>
          ) : node.children?.length ? (
            <details
              className="tree-group"
              open={props.open_ids.includes(node.id)}
            >
              <summary className="tree-summary">
                {node.title} {node.completed ? "✓" : ""}
              </summary>
              <a className="tree-link tree-overview" href={node.url}>
                {t("Обзор темы")}
              </a>
              <Tree nodes={node.children} depth={depth + 1} />
            </details>
          ) : (
            <a
              className={`tree-link ${props.current?.id === node.id ? "is-current" : ""}`}
              href={node.url}
            >
              {node.title}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
export default function Materials() {
  const { t, props: p, user, routes, language } = useByte();
  const [side, setSide] = useState(false);
  const c = p.current;
  return (
    <>
      <div className="dash">
        <aside
          className={`dash-side ${side ? "is-open" : ""}`}
          id="lesson-tree"
          aria-label={t("Темы ЕНТ")}
        >
          <span className="dash-side-title">{t("Материалы ЕНТ")}</span>
          <nav className="tree">
            <Tree nodes={p.roots} />
          </nav>
        </aside>
        <main className="dash-main">
          <button
            className="btn btn-ghost side-toggle"
            aria-expanded={side}
            aria-controls="lesson-tree"
            onClick={() => setSide(!side)}
          >
            ☰ {t("Разделы")}
          </button>
          {c ? (
            <>
              <nav className="crumbs">
                <a href={routes.dashboard}>{t("Материалы")}</a>
                {p.breadcrumbs.map((s) => (
                  <React.Fragment key={s.id}>
                    <span>/</span>
                    <a href={s.url}>{s.title}</a>
                  </React.Fragment>
                ))}
                <span>/ {c.title}</span>
              </nav>
              <article className="doc">
                <div className="lesson-heading">
                  <h1>{c.title}</h1>
                  {p.completed && (
                    <span className="status-pill status-done">
                      ✓ {t("тема пройдена")}
                    </span>
                  )}
                </div>
                <p className="doc-lead">{c.summary}</p>
                {externalURL(c.video_embed_url) && (
                  <section className="lesson-block">
                    <div className="lesson-block-head">
                      <h2>{t("Видеоразбор")}</h2>
                      <a
                        href={externalURL(c.video_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {t("Открыть отдельно ↗")}
                      </a>
                    </div>
                    <div className="video-frame">
                      <iframe
                        src={externalURL(c.video_embed_url)}
                        title={c.title}
                        loading="lazy"
                        referrerPolicy="strict-origin-when-cross-origin"
                        allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                  </section>
                )}
                {c.content ? (
                  <section className="lesson-block">
                    <h2>{t("Материал урока")}</h2>
                    <RichText html={c.content} />
                  </section>
                ) : (
                  !c.children.length &&
                  !c.video_url && (
                    <p className="doc-empty">
                      {t("Материал по этому уроку скоро появится.")}
                    </p>
                  )
                )}
                {!!c.children.length && (
                  <div className="doc-children">
                    <h2>{t("Что нужно пройти")}</h2>
                    <ul className="child-list">
                      {c.children.map((s, i) => (
                        <li key={s.id}>
                          <a className="child-link" href={s.url}>
                            <span className="child-order">{number(i + 1)}</span>
                            <span className="child-copy">
                              <strong>{s.title}</strong>
                              <span>{s.summary}</span>
                            </span>
                            <span>→</span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {c.id === p.current_root?.id && (
                  <section className="topic-checkpoint">
                    <div>
                      <h2>{t("Проверочный тест")}</h2>
                      <p>
                        {p.quiz
                          ? `${t("Проходной результат", "Өту шегі")}: ${p.quiz.pass_percent}%`
                          : t(
                              "Тест для этой темы пока настраивается преподавателем.",
                            )}
                      </p>
                      {p.best_score !== null && (
                        <span>
                          {t("Лучший результат")}: {p.best_score}%
                        </span>
                      )}
                    </div>
                    {p.quiz && (
                      <a className="btn btn-primary" href={p.quiz.url}>
                        {t(p.completed ? "Пройти ещё раз" : "Начать тест")}
                      </a>
                    )}
                  </section>
                )}
                <div className="doc-nav">
                  {p.previous && (
                    <a className="prev" href={p.previous.url}>
                      <span>{t("Назад")}</span>
                      <strong>{p.previous.title}</strong>
                    </a>
                  )}
                  {p.next_is_quiz ? (
                    <a className="next" href={p.quiz.url}>
                      {t("Пройти тест по теме →")}
                    </a>
                  ) : (
                    p.next && (
                      <a className="next" href={p.next.url}>
                        <span>{t("Дальше")}</span>
                        <strong>{p.next.title}</strong>
                      </a>
                    )
                  )}
                </div>
              </article>
            </>
          ) : (
            <div className="welcome">
              <span className="kicker">{t("кабинет ученика")}</span>
              <h1>
                {t("Привет", "Сәлем")}, {user.name}
              </h1>
              <p>
                {t(
                  "Темы открываются последовательно: завершите текущую тему и пройдите её тест, чтобы открыть следующую.",
                )}
              </p>
              {p.next_contest && (
                <div className="contest-banner">
                  <div>
                    <strong>{p.next_contest.title}</strong>
                    <p>
                      {dateTime(p.next_contest.starts_at, language)} ·{" "}
                      {p.next_contest.duration_minutes} {t("мин.")}
                    </p>
                  </div>
                  <a className="btn btn-primary" href={routes.contest}>
                    {t("Перейти к контесту")}
                  </a>
                </div>
              )}
              <div className="topic-grid learning-path-grid">
                {p.roots.map((s, i) => {
                  const Tag = s.locked ? "div" : "a";
                  return (
                    <Tag
                      key={s.id}
                      href={s.locked ? undefined : s.url}
                      className={`topic-card ${s.locked ? "topic-card-locked" : ""}`}
                      aria-disabled={s.locked || undefined}
                    >
                      <div className="topic-card-top">
                        <span>{number(i + 1)}</span>
                        <span>
                          {s.locked ? "🔒 " : s.completed ? "✓ " : ""}
                          {t(
                            s.locked
                              ? "закрыто"
                              : s.completed
                                ? "пройдено"
                                : "доступно",
                          )}
                        </span>
                      </div>
                      <h3>{s.title}</h3>
                      <p>{s.summary}</p>
                      <small>
                        {s.locked
                          ? t("Откроется после предыдущей темы")
                          : `${t("уроков")}: ${s.children.length}`}
                      </small>
                    </Tag>
                  );
                })}
              </div>
              {!p.roots.length && (
                <p className="doc-empty">
                  {t(
                    "Материалы пока не добавлены.",
                    "Материалдар әлі қосылмаған.",
                  )}
                </p>
              )}
            </div>
          )}
        </main>
      </div>
      {p.ai.enabled && <Assistant config={p.ai} title={c?.title} />}
    </>
  );
}
