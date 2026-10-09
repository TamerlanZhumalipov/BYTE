import React, { useEffect, useRef, useState } from "react";
import {
  useByte,
  PostForm,
  RichText,
  dateTime,
  number,
  requestJSON,
} from "../core";
export const formatTime = (s) =>
  `${number(Math.floor(s / 3600))}:${number(Math.floor(s / 60) % 60)}:${number(s % 60)}`;
function useCountdown(seconds) {
  const deadline = useRef(performance.now() + seconds * 1000),
    [left, setLeft] = useState(seconds);
  useEffect(() => {
    const tick = () =>
      setLeft(
        Math.max(0, Math.ceil((deadline.current - performance.now()) / 1000)),
      );
    const id = setInterval(tick, 250);
    return () => clearInterval(id);
  }, []);
  return [
    left,
    (remaining) => {
      deadline.current = performance.now() + Math.max(0, remaining) * 1000;
      setLeft(Math.max(0, remaining));
    },
  ];
}
const draft = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  },
};
const starter = {
  python: "# input() → print()\n",
  cpp: "#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}\n",
};
function Editor({ task, prefix, locked, busy, onSubmit }) {
  const { t } = useByte();
  const [lang, setLang] = useState(() =>
    draft.get(`${prefix}:lang:${task.id}`) === "cpp" ? "cpp" : "python",
  );
  const [code, setCode] = useState(
    () => draft.get(`${prefix}:code:${task.id}:${lang}`) ?? starter[lang],
  );
  const trap = useRef(true),
    editor = useRef(null);
  function edit(value) {
    setCode(value);
    draft.set(`${prefix}:code:${task.id}:${lang}`, value);
  }
  function language(value) {
    setLang(value);
    draft.set(`${prefix}:lang:${task.id}`, value);
    setCode(draft.get(`${prefix}:code:${task.id}:${value}`) ?? starter[value]);
  }
  return (
    <>
      <div className="cx-toolbar">
        <label className="cx-lang">
          {t("Язык")}{" "}
          <select
            value={lang}
            onChange={(e) => language(e.target.value)}
            disabled={locked || busy}
          >
            <option value="python">Python</option>
            <option value="cpp">C++</option>
          </select>
        </label>
        <button
          className="btn btn-primary"
          disabled={locked || busy || !code.trim()}
          onClick={() => onSubmit(task.id, lang, code)}
        >
          {t(
            busy ? "Проверяем на тестах…" : "Отправить решение",
            busy ? "Тесттерде тексерілуде…" : "Шешімді жіберу",
          )}
        </button>
      </div>
      <textarea
        ref={editor}
        className="cx-editor"
        value={code}
        onChange={(e) => edit(e.target.value)}
        rows={16}
        readOnly={locked}
        spellCheck={false}
        autoCapitalize="off"
        aria-label={t("Код решения")}
        onKeyDown={(e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            if (!locked && !busy && code.trim()) onSubmit(task.id, lang, code);
          }
          if (e.key === "Escape") trap.current = false;
          else if (e.key === "Tab" && !e.shiftKey && trap.current && !locked) {
            e.preventDefault();
            const at = e.currentTarget.selectionStart,
              end = e.currentTarget.selectionEnd;
            edit(code.slice(0, at) + "    " + code.slice(end));
            requestAnimationFrame(() =>
              editor.current?.setSelectionRange(at + 4, at + 4),
            );
          } else if (e.key !== "Tab" && e.key !== "Shift") trap.current = true;
        }}
      />
      <small>
        {t(
          "Ctrl/⌘ + Enter — отправить. Esc, затем Tab — выйти из редактора.",
          "Ctrl/⌘ + Enter — жіберу. Esc, одан кейін Tab — редактордан шығу.",
        )}
      </small>
    </>
  );
}
export default function Contest() {
  const { t, props: p, routes, csrf, language } = useByte();
  const [remaining, syncTime] = useCountdown(p.remaining);
  const [tasks, setTasks] = useState(p.tasks),
    [id, setId] = useState(p.tasks[0]?.id),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const inFlight = useRef(false);
  const [closed, setClosed] = useState(p.state === "finished");
  const waiting = p.state === "upcoming";
  const locked = closed || remaining === 0;
  const current = tasks.find((task) => task.id === id),
    latest = current?.history[0];
  useEffect(() => {
    if (waiting && remaining === 0) window.location.reload();
  }, [waiting, remaining]);
  async function submit(taskId, lang, code) {
    if (locked || inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await requestJSON(
        routes.contest_submit,
        csrf,
        { task_id: taskId, language: lang, code },
        t,
      );
      setTasks((list) =>
        list.map((task) =>
          task.id === taskId
            ? {
                ...task,
                best: result.best,
                history: [result.submission, ...task.history].slice(0, 8),
              }
            : task,
        ),
      );
      if (typeof result.remaining === "number") syncTime(result.remaining);
    } catch (e) {
      setError(e.message);
      if (e.state === "finished") setClosed(true);
    } finally {
      setBusy(false);
      inFlight.current = false;
    }
  }
  const logout = (
    <PostForm action={routes.contest_logout}>
      <button className="btn btn-ghost btn-sm">{t("Выйти из контеста")}</button>
    </PostForm>
  );
  if (waiting)
    return (
      <main className="auth-main">
        <div className="auth-card wait-card">
          <h1>{p.contest.title}</h1>
          <p>
            {t("Участник")}: {p.account.name || p.account.login}
          </p>
          <p>{dateTime(p.contest.starts_at, language)}</p>
          <div role="timer" className="cx-timer cx-timer-big">
            {formatTime(remaining)}
          </div>
          <p>{t("Страница обновится сама, как только контест начнётся.")}</p>
          {logout}
        </div>
      </main>
    );
  return (
    <main className="cx">
      <div className="cx-top">
        <div className="cx-title">
          {p.contest.title}
          <span className="cx-user">
            {p.account.name || p.account.login} · {p.account.login}
          </span>
        </div>
        <div className="cx-top-right">
          <div
            role="timer"
            aria-label={t("Оставшееся время")}
            className={`cx-timer ${remaining <= 300 ? "is-warn" : ""}`}
          >
            {formatTime(remaining)}
          </div>
          {logout}
        </div>
      </div>
      {locked && (
        <p className="cx-closed">
          {t(
            "Контест завершён. Отправка решений закрыта — ваши результаты сохранены.",
          )}
        </p>
      )}
      <div className="cx-tabs" aria-label={t("Задачи")}>
        {tasks.map((task, i) => (
          <button
            className={`cx-tab ${id === task.id ? "is-active" : ""}`}
            aria-pressed={id === task.id}
            disabled={busy}
            onClick={() => {
              setId(task.id);
              setError("");
            }}
            key={task.id}
          >
            <span className="cx-tab-num">{i + 1}</span>
            {task.title}
            <span className="cx-chip">
              {task.best}/{task.total}
            </span>
          </button>
        ))}
      </div>
      {current ? (
        <div className="cx-body">
          <article className="cx-statement doc">
            <h2>{current.title}</h2>
            <p className="cx-limits">
              {t("лимит")} {current.time_limit} {t("с на тест")} · {t("тестов")}
              : {current.total}
            </p>
            <RichText html={current.statement} />
          </article>
          <div className="cx-work">
            {error && (
              <p role="alert" className="react-error">
                {error}
              </p>
            )}
            <Editor
              key={id}
              task={current}
              prefix={`byte:${p.contest.id}:${p.account.id}`}
              locked={locked}
              busy={busy}
              onSubmit={submit}
            />
            <div className="cx-result" aria-live="polite">
              {latest ? (
                <>
                  <div className={`cx-verdict ${latest.verdict.toLowerCase()}`}>
                    {t(latest.label)} · {latest.passed}/{latest.total}
                  </div>
                  <div className="cx-grid">
                    {Array.from({ length: latest.total }, (_, i) => {
                      const mark = latest.marks?.[i] || "-";
                      return (
                        <span
                          key={i}
                          className={`cx-cell ${{ P: "p", F: "f", T: "t", E: "e" }[mark] || ""}`}
                          title={`${t("Тесты")}: ${i + 1}`}
                        >
                          {{ P: "✓", F: "×", T: "T", E: "!" }[mark] || "—"}
                        </span>
                      );
                    })}
                  </div>
                  {latest.message && (
                    <pre className="cx-message">{latest.message}</pre>
                  )}
                </>
              ) : (
                <p>
                  {t("Отправьте решение — здесь появится результат проверки.")}
                </p>
              )}
            </div>
            <div className="cx-history">
              <h3>{t("Ваши отправки по этой задаче")}</h3>
              <ul>
                {current.history.map((s) => (
                  <li key={s.id}>
                    <span>{t(s.label)}</span>
                    <span>
                      {s.passed}/{s.total}
                    </span>
                    <span>{s.language === "cpp" ? "C++" : "Python"}</span>
                    <span>{s.time}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <p className="doc-empty">
          {t("Задачи пока не добавлены.", "Есептер әлі қосылмаған.")}
        </p>
      )}
    </main>
  );
}
