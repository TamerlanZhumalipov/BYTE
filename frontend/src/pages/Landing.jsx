import React from "react";
import { useByte } from "../core";
import LeadForm from "../components/LeadForm";
export default function Landing() {
  const { t, language } = useByte();
  return (
    <main>
      <section className="hero">
        <div className="container">
          <div className="hero-copy">
            <span className="hero-lead">
              {t("курс по информатике · онлайн")}
            </span>
            <h1>
              {t(
                "Готовим к ЕНТ по информатике — и к первой строчке кода в резюме",
              )}
            </h1>
            <p className="hero-sub">
              {t(
                "Python, C++, SQL, HTML и CSS в одной программе: разбираем темы ЕНТ и одновременно учимся писать код, который решает настоящие задачи.",
              )}
            </p>
            <div className="hero-cta">
              <a className="btn btn-primary" href="#pricing">
                {t("Выбрать пакет")}
              </a>
              <a className="btn btn-ghost" href="#contests">
                {t("Как проходят контесты")}
              </a>
            </div>
            <div className="hero-stats">
              <div className="hero-stat">
                <strong>{t("5 направлений")}</strong>
                <span>Python, C++, SQL, HTML, CSS</span>
              </div>
              <div className="hero-stat">
                <strong>{t("Каждую субботу")}</strong>
                <span>{t("лайв-кодинг контест")}</span>
              </div>
              <div className="hero-stat">
                <strong>{t("2 формата")}</strong>
                <span>{t("самостоятельно или с ментором")}</span>
              </div>
            </div>
          </div>
          <div className="code-panel" aria-hidden="true">
            <div className="code-panel-bar">
              <span className="code-dot"></span>
              <span className="code-dot"></span>
              <span className="code-dot"></span>
              <span className="code-panel-title">contest_task.py</span>
              <span className="code-panel-live">live</span>
            </div>
            <pre className="code-panel-body">{`def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n\nprint(is_prime(17))`}</pre>
            <div className="code-panel-footer">
              <span className="test-check show">
                {language === "kk" ? (
                  <>✓ барлық тест өтті</>
                ) : (
                  <>✓ все тесты пройдены</>
                )}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section id="tracks">
        <div className="container">
          <div className="section-head">
            <h2>{t("Одна программа — пять направлений")}</h2>
            <p>
              {t(
                "Каждый язык закрывает свою часть ЕНТ по информатике и даёт отдельный практический навык.",
              )}
            </p>
          </div>
          <div className="tracks-grid">
            <div className="track-card">
              <span className="track-tag">
                01 · {language === "kk" ? <>негізгі тіл</> : <>основной язык</>}
              </span>
              <h3>Python</h3>
              <p>
                {language === "kk" ? (
                  <>
                    Синтаксис, циклдер, функциялар, тізімдер мен жолдар — ҰБТ
                    тапсырмаларының негізгі бөлігі.
                  </>
                ) : (
                  <>
                    Синтаксис, циклы, функции, работа со списками и строками —
                    основа большинства заданий ЕНТ.
                  </>
                )}
              </p>
            </div>
            <div className="track-card">
              <span className="track-tag">
                02 · {language === "kk" ? <>деректер қоры</> : <>базы данных</>}
              </span>
              <h3>SQL</h3>
              <p>
                {language === "kk" ? (
                  <>
                    Сұраныстар, таңдау және кестелерді біріктіру — мектепте аз
                    кездесетін, бірақ нақты әзірлеуде қажет дағдылар.
                  </>
                ) : (
                  <>
                    Запросы, выборки, соединение таблиц — то, что почти не
                    встречается в школьной программе, но нужно в реальной
                    разработке.
                  </>
                )}
              </p>
            </div>
            <div className="track-card">
              <span className="track-tag">
                03 · {language === "kk" ? <>алгоритмдер</> : <>алгоритмы</>}
              </span>
              <h3>C++</h3>
              <p>
                {language === "kk" ? (
                  <>
                    Типтер, жад және алгоритм күрделілігі — күрделі есептерді
                    талдауға ыңғайлы бағыт.
                  </>
                ) : (
                  <>
                    Типизация, память, сложность алгоритмов — язык, на котором
                    удобно разбирать олимпиадные задачи ЕНТ.
                  </>
                )}
              </p>
            </div>
            <div className="track-card">
              <span className="track-tag">
                04 · {language === "kk" ? <>белгілеу</> : <>разметка</>}
              </span>
              <h3>HTML</h3>
              <p>
                {language === "kk" ? (
                  <>
                    Бет құрылымы мен семантика — кодты көрінетін веб-интерфейске
                    айналдырудың алғашқы қадамы.
                  </>
                ) : (
                  <>
                    Структура страницы и семантика — первый шаг к тому, чтобы
                    код превращался во что-то видимое.
                  </>
                )}
              </p>
            </div>
            <div className="track-card">
              <span className="track-tag">
                05 · {language === "kk" ? <>стильдер</> : <>стили</>}
              </span>
              <h3>CSS</h3>
              <p>
                {language === "kk" ? (
                  <>
                    Безендіру, адаптивтілік және торлар — HTML беттерін толық
                    интерфейске айналдырамыз.
                  </>
                ) : (
                  <>
                    Оформление, адаптивность, сетки — доводим страницы на HTML
                    до законченного вида.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="ent">
        <div className="container">
          <div className="split">
            <div>
              <span className="kicker">{t("подготовка к экзамену")}</span>
              <h2>
                {t(
                  "Разбираем ЕНТ по информатике по темам, а не в общих словах",
                )}
              </h2>
              <p>
                {language === "kk" ? (
                  <>
                    Әр сабақ нақты ҰБТ блогына байланған: санау жүйелерінен
                    бастап логика, бағдарламалау және деректер қорына дейін.
                    Оқушы қай жерде ұпай жоғалтатынын көріп, дәл сол олқылықты
                    жабады.
                  </>
                ) : (
                  <>
                    Каждое занятие привязано к конкретному блоку экзамена: от
                    систем счисления и логики до написания и отладки программ.
                    Ученик видит, где именно в задании он теряет баллы, и
                    закрывает именно этот пробел.
                  </>
                )}
              </p>
            </div>
            <ul className="checklist">
              <li>
                <span className="mark">01</span>{" "}
                {language === "kk" ? (
                  <>Санау жүйелері және деректерді ұсыну</>
                ) : (
                  <>Системы счисления и представление данных</>
                )}
              </li>
              <li>
                <span className="mark">02</span>{" "}
                {language === "kk" ? (
                  <>Алгоритмдер, циклдер және тармақталу</>
                ) : (
                  <>Алгоритмы, циклы и ветвления</>
                )}
              </li>
              <li>
                <span className="mark">03</span>{" "}
                {language === "kk" ? (
                  <>Массивтер, жолдар және деректер құрылымдары</>
                ) : (
                  <>Массивы, строки и структуры данных</>
                )}
              </li>
              <li>
                <span className="mark">04</span>{" "}
                {language === "kk" ? (
                  <>Логикалық функциялар және ақиқат кестелері</>
                ) : (
                  <>Логические функции и таблицы истинности</>
                )}
              </li>
              <li>
                <span className="mark">05</span>{" "}
                {language === "kk" ? (
                  <>Python бағдарламаларын жазу және жөндеу</>
                ) : (
                  <>Написание и отладка программ на Python</>
                )}
              </li>
              <li>
                <span className="mark">06</span>{" "}
                {language === "kk" ? (
                  <>SQL негізгі сұраныстары</>
                ) : (
                  <>Базовые SQL-запросы к таблицам</>
                )}
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section id="contests">
        <div className="container">
          <div className="section-head">
            <h2>{t("По субботам — лайв-кодинг контест")}</h2>
            <p>
              {language === "kk" ? (
                <>
                  Оқушылар нақты уақытта есеп шешіп, өз шешімін қорғайды және
                  ментордан талдау алады — бәрі BYTE ішінде.
                </>
              ) : (
                <>
                  Ученики решают задачу в реальном времени, защищают своё
                  решение и получают разбор от ментора — прямо на сайте курса.
                </>
              )}
            </p>
          </div>
          <div className="contest-wrap">
            <div>
              <div className="contest-schedule">
                <span className="day-chip">
                  {language === "kk" ? <>дс</> : <>пн</>}
                </span>
                <span className="day-chip">
                  {language === "kk" ? <>сс</> : <>вт</>}
                </span>
                <span className="day-chip">
                  {language === "kk" ? <>ср</> : <>ср</>}
                </span>
                <span className="day-chip">
                  {language === "kk" ? <>бс</> : <>чт</>}
                </span>
                <span className="day-chip">
                  {language === "kk" ? <>жм</> : <>пт</>}
                </span>
                <span className="day-chip active">
                  {language === "kk" ? <>сб</> : <>сб</>}
                </span>
                <span className="day-chip">
                  {language === "kk" ? <>жс</> : <>вс</>}
                </span>
              </div>
              <p style={{ marginBottom: 16 }}>
                {language === "kk" ? (
                  <>
                    Контест бір сағатқа созылады: 20 минут есепке, қалған уақыт
                    шешімдерді талдауға және сұрақтарға.
                  </>
                ) : (
                  <>
                    Контест длится час: 20 минут на задачу, остальное время — на
                    разбор решений и вопросы.
                  </>
                )}
              </p>
              <p>
                {language === "kk" ? (
                  <>
                    Нәтижелер жеке кабинетте сақталып, контесттен контестке
                    дейінгі прогресті көрсетеді.
                  </>
                ) : (
                  <>
                    Результаты сохраняются в личном кабинете, чтобы было видно
                    прогресс от контеста к контесту.
                  </>
                )}
              </p>
            </div>
            <div className="leaderboard">
              <div className="leaderboard-head">
                <span>{language === "kk" ? <>қатысушы</> : <>участник</>}</span>
                <span>
                  {language === "kk" ? <>өткен тест</> : <>тестов пройдено</>}
                </span>
              </div>
              <div className="lb-row">
                <span className="lb-rank">1</span>
                <span className="lb-name">
                  {language === "kk" ? <>Ойыншы 1</> : <>Игрок 1</>}
                </span>
                <span className="lb-score">12/12</span>
              </div>
              <div className="lb-row">
                <span className="lb-rank">2</span>
                <span className="lb-name">
                  {language === "kk" ? <>Ойыншы 2</> : <>Игрок 2</>}
                </span>
                <span className="lb-score">11/12</span>
              </div>
              <div className="lb-row">
                <span className="lb-rank">3</span>
                <span className="lb-name">
                  {language === "kk" ? <>Ойыншы 3</> : <>Игрок 3</>}
                </span>
                <span className="lb-score">9/12</span>
              </div>
              <div className="lb-note">
                {language === "kk" ? (
                  <>
                    Контест кестесінің мысалы — нақты есімдер іске қосылғаннан
                    кейін пайда болады.
                  </>
                ) : (
                  <>
                    Пример таблицы контеста — реальные имена появятся после
                    запуска.
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="pricing">
        <div className="container">
          <div className="section-head">
            <h2>{t("Два пакета — выберите глубину погружения")}</h2>
            <p>
              {language === "kk" ? (
                <>
                  Екі пакет те материалдар мен сенбілік контесттерге
                  қолжетімділік береді.
                </>
              ) : (
                <>Оба открывают доступ к материалам и субботним контестам.</>
              )}
            </p>
          </div>
          <div className="pricing-table">
            <div className="pricing-row pricing-header">
              <div className="pricing-cell"></div>
              <div className="pricing-cell">
                <h3>Старт</h3>
                <div className="price">
                  9 900 ₸
                  <span> / {language === "kk" ? <>ай</> : <>мес</>}</span>
                </div>
              </div>
              <div className="pricing-cell">
                <h3>Ментор</h3>
                <div className="price">
                  24 900 ₸
                  <span> / {language === "kk" ? <>ай</> : <>мес</>}</span>
                </div>
              </div>
            </div>
            <div className="pricing-row">
              <div className="pricing-cell feature-name">
                {language === "kk" ? (
                  <>Курс материалдарына қолжетімділік</>
                ) : (
                  <>Доступ к материалам курса</>
                )}
              </div>
              <div className="pricing-cell">
                <span className="yes">✓</span>
              </div>
              <div className="pricing-cell">
                <span className="yes">✓</span>
              </div>
            </div>
            <div className="pricing-row">
              <div className="pricing-cell feature-name">
                {language === "kk" ? (
                  <>Лайв-кодинг контесттері</>
                ) : (
                  <>Лайв-кодинг контесты</>
                )}
              </div>
              <div className="pricing-cell">
                <span className="yes">✓</span>
              </div>
              <div className="pricing-cell">
                <span className="yes">✓</span>
              </div>
            </div>
            <div className="pricing-row">
              <div className="pricing-cell feature-name">
                {language === "kk" ? (
                  <>Жеке ментор және онлайн-сабақтар</>
                ) : (
                  <>Личный ментор и онлайн-уроки</>
                )}
              </div>
              <div className="pricing-cell">
                <span className="no">—</span>
              </div>
              <div className="pricing-cell">
                <span className="yes">✓</span>
              </div>
            </div>
            <div className="pricing-row pricing-cta-row">
              <div className="pricing-cell feature-name"></div>
              <div className="pricing-cell">
                <a className="btn btn-ghost btn-block" href="/?plan=start#cta">
                  {language === "kk" ? (
                    <>«Старт» таңдау</>
                  ) : (
                    <>Выбрать «Старт»</>
                  )}
                </a>
              </div>
              <div className="pricing-cell">
                <a
                  className="btn btn-primary btn-block"
                  href="/?plan=mentor#cta"
                >
                  {language === "kk" ? (
                    <>«Ментор» таңдау</>
                  ) : (
                    <>Выбрать «Ментор»</>
                  )}
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="format">
        <div className="container">
          <div className="section-head">
            <h2>{t("Как проходит обучение")}</h2>
            <p>
              {language === "kk" ? (
                <>
                  Икемді формат: өз қарқыныңызбен немесе оқытушымен бірге оқуға
                  болады.
                </>
              ) : (
                <>
                  Гибкий формат: заниматься можно в своём темпе или вместе с
                  преподавателем.
                </>
              )}
            </p>
          </div>
          <div className="format-grid">
            <div className="format-card">
              <h3>
                {language === "kk" ? (
                  <>Курс материалдары</>
                ) : (
                  <>Материалы курса</>
                )}
              </h3>
              <p>
                {language === "kk" ? (
                  <>
                    Әр бағыт бойынша құрылымдалған сабақтар, тапсырмалар және
                    ҰБТ-ның типтік есептерін талдау.
                  </>
                ) : (
                  <>
                    Структурированные уроки по каждому языку с заданиями и
                    разбором типовых задач ЕНТ.
                  </>
                )}
              </p>
            </div>
            <div className="format-card">
              <h3>
                {language === "kk" ? <>Лайв-сабақтар</> : <>Лайв-уроки</>}
              </h3>
              <p>
                {language === "kk" ? (
                  <>
                    Оқытушыға сұрақ қойып, бірден жауап алуға болатын тұрақты
                    онлайн-сабақтар.
                  </>
                ) : (
                  <>
                    Регулярные онлайн-занятия, где можно задать вопрос
                    преподавателю и сразу получить ответ.
                  </>
                )}
              </p>
            </div>
            <div className="format-card">
              <h3>Лайв-кодинг</h3>
              <p>
                {language === "kk" ? (
                  <>
                    Техникалық есептерді дауыстап талдаймыз: шешім барысын
                    түсіндіріп, кодты қорғауды үйренеміз.
                  </>
                ) : (
                  <>
                    Разбор технических задач вслух: учимся объяснять ход решения
                    и защищать свой код.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="faq">
        <div className="container">
          <div className="section-head">
            <h2>{t("Частые вопросы")}</h2>
          </div>
          <div className="faq-list">
            <details className="faq-item">
              <summary>
                {language === "kk" ? (
                  <>Нөлден бастасам, курс жарай ма?</>
                ) : (
                  <>Подойдёт ли курс, если я начинаю с нуля?</>
                )}
              </summary>
              <p>
                {language === "kk" ? (
                  <>
                    Иә. Бағдарлама негізгі ұғымдардан практикалық есептерге
                    дейін құрылған.
                  </>
                ) : (
                  <>
                    Да. Программа построена от базовых понятий к практическим
                    задачам.
                  </>
                )}
              </p>
            </details>
            <details className="faq-item">
              <summary>
                {language === "kk" ? (
                  <>Қуатты компьютер керек пе?</>
                ) : (
                  <>Нужен ли мощный компьютер?</>
                )}
              </summary>
              <p>
                {language === "kk" ? (
                  <>Жоқ. Кәдімгі ноутбук пен браузер жеткілікті.</>
                ) : (
                  <>Нет. Для занятий достаточно обычного ноутбука и браузера.</>
                )}
              </p>
            </details>
            <details className="faq-item">
              <summary>
                {language === "kk" ? (
                  <>Контесттерде не болады?</>
                ) : (
                  <>Что происходит на контестах?</>
                )}
              </summary>
              <p>
                {language === "kk" ? (
                  <>
                    Оқушы есеп алып, шешімін жазады және автоматты тест
                    нәтижесін бірден көреді.
                  </>
                ) : (
                  <>
                    Ученик получает задачи, пишет решение и сразу видит
                    результат автоматических тестов.
                  </>
                )}
              </p>
            </details>
          </div>
        </div>
      </section>

      <section id="cta">
        <div className="container">
          <div className="cta-box">
            <div>
              <span className="kicker">{t("набор открыт")}</span>
              <h2>{t("Оставьте заявку — расскажем, с чего начать")}</h2>
              <p>
                {language === "kk" ? (
                  <>
                    Форманы толтырыңыз, біз сізбен көрсетілген байланыс арқылы
                    хабарласамыз.
                  </>
                ) : (
                  <>
                    Заполните форму, и мы свяжемся с вами по выбранному
                    контакту.
                  </>
                )}
              </p>
            </div>
            <LeadForm />
          </div>
        </div>
      </section>
    </main>
  );
}
