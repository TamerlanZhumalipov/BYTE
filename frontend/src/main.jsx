import React, { Component, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { ByteProvider, useByte } from "./core";
import Header from "./components/Header";
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Materials from "./pages/Materials";
import Quiz from "./pages/Quiz";
import Analytics from "./pages/Analytics";
import Contest from "./pages/Contest";
import "./react.css";
class ErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="auth-main">
        <div className="auth-card">
          <h1>BYTE</h1>
          <p>
            {this.props.language === "kk"
              ? "Бет жүктелмеді. Қайта жүктеңіз."
              : "Не удалось отобразить страницу. Попробуйте обновить её."}
          </p>
          <button className="btn btn-primary" onClick={() => location.reload()}>
            {this.props.language === "kk" ? "Жаңарту" : "Обновить"}
          </button>
        </div>
      </main>
    ) : (
      this.props.children
    );
  }
}
function App() {
  const { page, props, messages, t, routes, logo } = useByte();
  useEffect(() => {
    const title =
      props.current?.title ||
      props.topic?.title ||
      props.contest?.title ||
      t(
        {
          index: "Подготовка к ЕНТ",
          login: "Войти",
          dashboard: "Материалы",
          analytics: "Аналитика",
          contest_login: "Вход в контест",
        }[page] || "BYTE",
      );
    document.title = `${title} — BYTE`;
  }, [page]);
  const pages = {
    index: <Landing />,
    login: <Auth />,
    contest_login: <Auth contest />,
    dashboard: <Materials />,
    topic_quiz: <Quiz />,
    analytics: <Analytics />,
    contest: <Contest />,
  };
  return (
    <>
      <a className="skip-link" href="#page-content">
        {t("К содержимому", "Мазмұнға өту")}
      </a>
      <Header />
      <div id="page-content" tabIndex={-1}>
        {!!messages.length && (
          <div className="app-messages react-messages" role="status">
            {messages.map((m, i) => (
              <p key={i} className={`app-message app-message-${m.level}`}>
                {m.text}
              </p>
            ))}
          </div>
        )}
        {pages[page] || <p>{t("Страница не найдена", "Бет табылмады")}</p>}
      </div>
      {page === "index" && (
        <footer>
          <div className="container">
            <a className="brand" href={routes.index}>
              <img src={logo} alt="" />
              BYTE
            </a>
            <p>
              {t(
                "Подготовка к ЕНТ по информатике",
                "Информатикадан ҰБТ-ға дайындық",
              )}
            </p>
          </div>
        </footer>
      )}
    </>
  );
}
const data = JSON.parse(document.getElementById("byte-bootstrap").textContent);
createRoot(document.getElementById("root")).render(
  <ErrorBoundary language={data.language}>
    <ByteProvider data={data}>
      <App />
    </ByteProvider>
  </ErrorBoundary>,
);
