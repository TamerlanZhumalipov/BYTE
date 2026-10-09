import React, { createContext, useContext, useState } from "react";
import DOMPurify from "dompurify";

const ByteContext = createContext(null);
export function ByteProvider({ data, children }) {
  const value = {
    ...data,
    t: (ru, kk) =>
      data.language === "kk" ? (kk ?? data.translations[ru] ?? ru) : ru,
  };
  return <ByteContext.Provider value={value}>{children}</ByteContext.Provider>;
}
export const useByte = () => useContext(ByteContext);
export function CSRF() {
  return (
    <input type="hidden" name="csrfmiddlewaretoken" value={useByte().csrf} />
  );
}
export function PostForm({ children, onSubmit, ...props }) {
  const [pending, setPending] = useState(false);
  return (
    <form
      method="post"
      {...props}
      onSubmit={(event) => {
        if (pending) {
          event.preventDefault();
          return;
        }
        onSubmit?.(event);
        if (!event.defaultPrevented) setPending(true);
      }}
      aria-busy={pending}
    >
      <CSRF />
      {children}
    </form>
  );
}
export function RichText({ html, className = "doc-body" }) {
  // Only authored lesson/task HTML uses this component. Chat and errors use text.
  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html || "") }}
    />
  );
}
export function externalURL(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}
export function dateTime(value, language = "ru") {
  if (!value) return "—";
  return new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : "ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Almaty",
  }).format(new Date(value));
}
export const number = (value) => String(value).padStart(2, "0");
export async function requestJSON(url, csrf, body, t = (x) => x) {
  const options = {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": csrf },
  };
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(
      t(
        "Нет связи с сервером. Попробуйте ещё раз.",
        "Сервермен байланыс жоқ. Қайта көріңіз.",
      ),
    );
  }
  if (response.redirected)
    throw new Error(t("Войдите в аккаунт снова.", "Аккаунтқа қайта кіріңіз."));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      data.error ||
      (data.errors && Object.values(data.errors).flat().join(" ")) ||
      t(
        "Не удалось выполнить запрос. Обновите страницу и попробуйте снова.",
        "Сұрау орындалмады. Бетті жаңартып, қайта көріңіз.",
      );
    const error = new Error(t(message));
    error.state = data.state;
    throw error;
  }
  return data;
}
export const storage = {
  get(type, key, fallback) {
    try {
      return JSON.parse(window[type].getItem(key)) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(type, key, value) {
    try {
      window[type].setItem(key, JSON.stringify(value));
    } catch {
      /* Optional storage. */
    }
  },
};
