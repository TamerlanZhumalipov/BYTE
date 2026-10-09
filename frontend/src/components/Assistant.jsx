import React, { useEffect, useRef, useState } from "react";
import { useByte, requestJSON, storage } from "../core";
export default function Assistant({ config, title }) {
  const { t, user, csrf } = useByte();
  const key = `byte-ai-session:${user.id}:${config.ask_url}`;
  const [history, setHistory] = useState(() => {
    const h = storage.get("sessionStorage", key, []);
    return Array.isArray(h)
      ? h
          .filter(
            (m) =>
              m &&
              ["user", "assistant"].includes(m.role) &&
              typeof m.content === "string",
          )
          .slice(-16)
      : [];
  });
  const [open, setOpen] = useState(false),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const input = useRef(null),
    feed = useRef(null),
    fab = useRef(null),
    inFlight = useRef(false);
  useEffect(
    () => storage.set("sessionStorage", key, history.slice(-16)),
    [history, key],
  );
  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);
  useEffect(() => {
    if (feed.current) feed.current.scrollTop = feed.current.scrollHeight;
  }, [history, busy, open]);
  function close() {
    setOpen(false);
    fab.current?.focus();
  }
  useEffect(() => {
    function escape(e) {
      if (e.key === "Escape" && open) close();
    }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [open]);
  async function send(e) {
    e.preventDefault();
    if (!text.trim() || inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    const message = text.trim();
    const prior = history.slice(-8);
    setHistory((h) => [...h, { role: "user", content: message }].slice(-16));
    setText("");
    try {
      const data = await requestJSON(
        config.ask_url,
        csrf,
        { message, history: prior },
        t,
      );
      setHistory((h) =>
        [
          ...h,
          {
            role: "assistant",
            content:
              data.content ||
              t("Ответ пуст. Попробуйте ещё раз.", "Жауап бос. Қайта көріңіз."),
          },
        ].slice(-16),
      );
    } catch (e) {
      setError(e.message);
      setText(message);
    } finally {
      setBusy(false);
      inFlight.current = false;
      input.current?.focus();
    }
  }
  async function reset() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setHistory([]);
    setError("");
    try {
      await requestJSON(config.reset_url, csrf, undefined, t);
    } catch {
      /* Local history remains cleared. */
    } finally {
      inFlight.current = false;
      setBusy(false);
      input.current?.focus();
    }
  }
  return (
    <div className={`ai ${open ? "is-open" : ""}`} id="ai">
      <button
        ref={fab}
        className={`ai-fab ${open ? "is-open" : ""}`}
        type="button"
        aria-expanded={open}
        aria-controls="ai-panel"
        onClick={() => (open ? close() : setOpen(true))}
      >
        <span className="ai-star">✦</span>
        <span className="ai-fab-copy">
          <strong>BYTE AI</strong>
          <small>{t("Спросить помощника", "Көмекшіден сұрау")}</small>
        </span>
      </button>
      {open && (
        <div
          className="ai-panel"
          id="ai-panel"
          role="dialog"
          aria-label="BYTE AI"
        >
          <div className="ai-panel-head">
            <div>
              <strong>BYTE AI</strong>
              <span>
                {title ||
                  t("Помощник по BYTE и ЕНТ", "BYTE және ҰБТ көмекшісі")}
              </span>
            </div>
            <div className="ai-panel-actions">
              <button
                className="btn btn-ghost btn-sm"
                disabled={busy}
                onClick={reset}
              >
                {t("Новый диалог", "Жаңа диалог")}
              </button>
              <button
                className="ai-close"
                onClick={close}
                aria-label={t("Свернуть", "Жию")}
              >
                ×
              </button>
            </div>
          </div>
          <div className="ai-messages" ref={feed} role="log" aria-live="polite">
            {!history.length && (
              <div className="ai-msg ai-msg-assistant">
                <div className="ai-bubble">
                  {t(
                    "Привет! Я BYTE AI. Помогу разобраться с темой, кодом или подготовкой к ЕНТ.",
                    "Сәлем! Мен BYTE AI. Тақырыпты, кодты немесе ҰБТ-ға дайындықты түсінуге көмектесемін.",
                  )}
                </div>
              </div>
            )}
            {history.map((m, i) => (
              <div key={i} className={`ai-msg ai-msg-${m.role}`}>
                <div className="ai-bubble">{m.content}</div>
              </div>
            ))}
            {busy && (
              <p role="status">{t("Готовлю ответ…", "Жауап дайындаудамын…")}</p>
            )}
          </div>
          {error && (
            <p role="alert" className="react-error">
              {error}
            </p>
          )}
          <form className="ai-form" onSubmit={send}>
            <textarea
              ref={input}
              aria-label={t("Вопрос BYTE AI", "BYTE AI сұрағы")}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  e.currentTarget.form.requestSubmit();
                }
              }}
              placeholder={t("Спросите BYTE AI…", "BYTE AI-дан сұраңыз…")}
              maxLength={2000}
              rows={2}
              required
            />
            <button
              className="btn btn-primary btn-sm"
              disabled={busy || !text.trim()}
              aria-label={t("Отправить", "Жіберу")}
            >
              ↑
            </button>
          </form>
          <p className="ai-hint">
            {t(
              "История хранится только в текущей вкладке. Важные ответы лучше перепроверять.",
              "Тарих тек осы бетте сақталады. Маңызды жауаптарды қайта тексеріңіз.",
            )}
          </p>
        </div>
      )}
    </div>
  );
}
