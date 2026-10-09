import React from "react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
  act,
} from "@testing-library/react";
import { ByteProvider, RichText, requestJSON } from "./core";
import Header from "./components/Header";
import Assistant from "./components/Assistant";
import Forecast from "./components/Forecast";
import LeadForm from "./components/LeadForm";
import Quiz from "./pages/Quiz";
import Contest from "./pages/Contest";

const base = {
  page: "dashboard",
  language: "ru",
  csrf: "csrf-test",
  path: "/app/",
  logo: "/logo.jpg",
  user: { id: 1, name: "Test", username: "test" },
  translations: {},
  messages: [],
  routes: {
    index: "/",
    login: "/login/",
    logout: "/logout/",
    set_language: "/language/",
    dashboard: "/app/",
    analytics: "/app/analytics/",
    lead_create: "/api/leads/",
    contest: "/contest/",
    contest_submit: "/contest/submit/",
    contest_logout: "/contest/logout/",
  },
  props: {},
};
function mount(component, overrides = {}) {
  return render(
    <ByteProvider data={{ ...base, ...overrides }}>{component}</ByteProvider>,
  );
}
beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("keeps language and logout as CSRF protected POST forms", () => {
  mount(<Header />);
  const form = screen.getByRole("button", { name: "KZ" }).closest("form");
  expect(form.method).toBe("post");
  expect(form.action).toContain("/language/");
  expect(new FormData(form).get("csrfmiddlewaretoken")).toBe("csrf-test");
  expect(new FormData(form).get("next")).toBe("/app/");
  expect(
    screen.getByRole("button", { name: "Выйти" }).closest("form").action,
  ).toContain("/logout/");
});
it("mobile menu and theme work without legacy DOM scripts", () => {
  mount(<Header />);
  const button = screen.getByRole("button", { name: "Меню" });
  fireEvent.click(button);
  expect(button.getAttribute("aria-expanded")).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: "Светлая тема" }));
  expect(localStorage.getItem("byte-theme")).toBe("light");
  document.documentElement.classList.remove("light-theme");
});
it("sanitizes authored markup while keeping code and tables", () => {
  const { container } = mount(
    <RichText
      html={
        '<script>alert(1)</script><img src=x onerror="alert(1)"><a href="javascript:alert(1)">bad</a><pre><code>x &lt; 2</code></pre><table><tbody><tr><td>safe</td></tr></tbody></table>'
      }
    />,
  );
  expect(container.querySelector("script")).toBeNull();
  expect(container.querySelector("img").getAttribute("onerror")).toBeNull();
  expect(container.querySelector("a").getAttribute("href")).toBeNull();
  expect(screen.getByText("x < 2")).toBeTruthy();
  expect(screen.getByText("safe")).toBeTruthy();
});
it("quiz submits the original field contract and CSRF token", () => {
  const props = {
    topic: { id: 1, title: "Topic", url: "/app/materials/topic/" },
    pass_percent: 70,
    best_score: null,
    result: null,
    questions: [
      {
        id: 7,
        text: "Question",
        choices: [
          { id: 12, text: "Choice A" },
          { id: 13, text: "Choice B" },
        ],
      },
    ],
  };
  mount(<Quiz />, { props, path: "/app/materials/topic/quiz/" });
  fireEvent.click(screen.getByRole("radio", { name: "Choice B" }));
  const form = screen
    .getByRole("button", { name: "Завершить тест" })
    .closest("form");
  const data = new FormData(form);
  expect(data.get("q_7")).toBe("13");
  expect(data.get("csrfmiddlewaretoken")).toBe("csrf-test");
  expect(form.method).toBe("post");
});
it("quiz result shows next topic only if backend provides it", () => {
  mount(<Quiz />, {
    props: {
      topic: { id: 1, title: "Topic", url: "/topic/" },
      pass_percent: 70,
      best_score: 100,
      result: {
        passed: true,
        score: 100,
        correct_count: 1,
        total: 1,
        next: { url: "/next/" },
        review: [],
      },
    },
  });
  expect(
    screen
      .getByRole("link", { name: "Перейти к следующей теме →" })
      .getAttribute("href"),
  ).toBe("/next/");
});
it("chat sends JSON and CSRF and renders replies as text", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue({
      ok: true,
      redirected: false,
      json: async () => ({ content: "<img src=x onerror=alert(1)>" }),
    });
  vi.stubGlobal("fetch", fetchMock);
  mount(<Assistant config={{ ask_url: "/ask/", reset_url: "/reset/" }} />);
  fireEvent.click(screen.getByRole("button", { name: /BYTE AI/ }));
  fireEvent.change(screen.getByRole("textbox", { name: "Вопрос BYTE AI" }), {
    target: { value: "Explain" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Отправить" }));
  await screen.findByText("<img src=x onerror=alert(1)>");
  expect(document.querySelector(".ai-bubble img")).toBeNull();
  const options = fetchMock.mock.calls[0][1];
  expect(options.headers["X-CSRFToken"]).toBe("csrf-test");
  expect(JSON.parse(options.body)).toEqual({ message: "Explain", history: [] });
  fireEvent.click(screen.getByRole("button", { name: "Новый диалог" }));
  await waitFor(() => expect(screen.queryByText("Explain")).toBeNull());
});
it("chat never restores a different user session", () => {
  sessionStorage.setItem(
    "byte-ai-session:2:/ask/",
    JSON.stringify([{ role: "assistant", content: "PRIVATE MESSAGE" }]),
  );
  mount(<Assistant config={{ ask_url: "/ask/", reset_url: "/reset/" }} />);
  fireEvent.click(screen.getByRole("button", { name: /BYTE AI/ }));
  expect(screen.queryByText("PRIVATE MESSAGE")).toBeNull();
});
it("expired authentication redirects become a readable error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ redirected: true }));
  await expect(requestJSON("/ask/", "token", {})).rejects.toThrow(
    "Войдите в аккаунт снова.",
  );
});
it("lead submission preserves field values and shows backend validation", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        redirected: false,
        json: async () => ({ errors: { phone: ["Invalid phone"] } }),
      }),
  );
  mount(<LeadForm />);
  fireEvent.change(screen.getByRole("textbox", { name: "Имя" }), {
    target: { value: "Demo" },
  });
  fireEvent.change(
    screen.getByRole("textbox", { name: "Телефон или Telegram" }),
    { target: { value: "invalid" } },
  );
  fireEvent.submit(
    screen.getByRole("button", { name: "Отправить заявку" }).closest("form"),
  );
  await screen.findByText("Invalid phone");
  expect(screen.getByRole("textbox", { name: "Имя" }).value).toBe("Demo");
});
const contestProps = {
  state: "running",
  remaining: 600,
  contest: { id: 1, title: "Contest", duration_minutes: 10 },
  account: { id: 2, login: "demo" },
  tasks: [
    {
      id: 11,
      title: "Task 1",
      statement: "<p>Statement</p>",
      time_limit: 2,
      total: 1,
      best: 0,
      history: [],
    },
    {
      id: 12,
      title: "Task 2",
      statement: "Other",
      time_limit: 2,
      total: 1,
      best: 0,
      history: [],
    },
  ],
};
it("contest restores drafts across tasks and languages and submits correct task", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue({
      ok: true,
      redirected: false,
      json: async () => ({
        remaining: 590,
        best: 1,
        submission: {
          id: 1,
          label: "Принято",
          verdict: "OK",
          passed: 1,
          total: 1,
          marks: "P",
          language: "python",
          time: "10:00",
        },
      }),
    });
  vi.stubGlobal("fetch", fetchMock);
  mount(<Contest />, { props: contestProps });
  fireEvent.change(screen.getByRole("textbox", { name: "Код решения" }), {
    target: { value: "print(1)" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Task 2/ }));
  fireEvent.click(screen.getByRole("button", { name: /Task 1/ }));
  expect(screen.getByRole("textbox", { name: "Код решения" }).value).toBe(
    "print(1)",
  );
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "cpp" } });
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "python" },
  });
  expect(screen.getByRole("textbox", { name: "Код решения" }).value).toBe(
    "print(1)",
  );
  fireEvent.click(screen.getByRole("button", { name: "Отправить решение" }));
  await screen.findByText("Принято · 1/1");
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    task_id: 11,
    language: "python",
    code: "print(1)",
  });
});
it("contest closes submission when the countdown expires", () => {
  vi.useFakeTimers();
  mount(<Contest />, { props: { ...contestProps, remaining: 1 } });
  act(() => vi.advanceTimersByTime(1500));
  expect(
    screen.getByRole("button", { name: "Отправить решение" }).disabled,
  ).toBe(true);
  expect(screen.getByRole("textbox", { name: "Код решения" }).readOnly).toBe(
    true,
  );
});
it("forecast displays zero as a score and shows translated labels", () => {
  const data = {
    status: "ready",
    score: 0,
    max_score: 50,
    low: 0,
    high: 9,
    delta: 0,
    confidence: "low",
    quiz_count: 0,
    contest_count: 0,
    mock_count: 1,
    coverage_percent: 0,
    recommendations: [],
    topics: [],
    history: [],
    topic_count: 13,
    equal_weights: true,
  };
  mount(<Forecast data={data} />, {
    language: "kk",
    translations: { "Если сдавать ЕНТ сегодня": "ҰБТ-ны бүгін тапсырсаңыз" },
  });
  expect(
    screen.getByRole("heading", { name: "ҰБТ-ны бүгін тапсырсаңыз" }),
  ).toBeTruthy();
  expect(screen.getByText("≈ 0", { exact: false })).toBeTruthy();
  expect(screen.queryByText("Пока недостаточно данных")).toBeNull();
});
