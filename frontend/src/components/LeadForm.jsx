import React, { useState, useRef } from "react";
import { useByte, CSRF, requestJSON } from "../core";
export default function LeadForm() {
  const { t, routes, csrf } = useByte();
  const [busy, setBusy] = useState(false),
    [status, setStatus] = useState(""),
    [error, setError] = useState(false);
  const sending = useRef(false);
  const selected = new URLSearchParams(window.location.search).get("plan");
  async function send(e) {
    e.preventDefault();
    if (sending.current) return;
    const form = e.currentTarget;
    sending.current = true;
    setBusy(true);
    setStatus("");
    try {
      const data = await requestJSON(
        routes.lead_create,
        csrf,
        new FormData(form),
        t,
      );
      setStatus(data.message);
      setError(false);
      form.reset();
    } catch (e) {
      setStatus(e.message);
      setError(true);
    } finally {
      setBusy(false);
      sending.current = false;
    }
  }
  return (
    <form
      className="lead-form"
      action={routes.lead_create}
      method="post"
      onSubmit={send}
    >
      <CSRF />
      <input
        name="name"
        aria-label={t("Имя")}
        placeholder={t("Имя")}
        maxLength={120}
        required
      />
      <input
        name="phone"
        aria-label={t("Телефон или Telegram")}
        placeholder={t("Телефон или Telegram")}
        maxLength={32}
        required
      />
      <select
        name="plan"
        aria-label={t("Выберите пакет")}
        defaultValue={["start", "mentor"].includes(selected) ? selected : ""}
      >
        <option value="">{t("Выберите пакет")}</option>
        <option value="start">Старт</option>
        <option value="mentor">Ментор</option>
      </select>
      <button className="btn btn-primary" disabled={busy}>
        {t(
          busy ? "Отправка…" : "Отправить заявку",
          busy ? "Жіберілуде…" : undefined,
        )}
      </button>
      <p
        className={`form-status ${error ? "react-error" : ""}`}
        role={error ? "alert" : "status"}
      >
        {status}
      </p>
    </form>
  );
}
