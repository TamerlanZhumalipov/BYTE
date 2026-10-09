# React frontend

All public/student screens are now React components: landing/sign-up, login,
materials/lesson navigation, quizzes/review, analytics/Forecast, contest login,
waiting room, editor/results and BYTE AI chat. Django admin remains Django admin.
The existing visual tokens and styles remain in `static/css`; React-specific
responsive header styles live in `frontend/src/react.css`.

## Run the site after merging

The production bundle and Vite manifest are committed in `static/react` so an
ordinary Python-only installation does not require Node to start the site:

```sh
git pull origin main
python manage.py migrate
python manage.py runserver
```

No new database migration is introduced by the frontend change. `migrate` also
applies any earlier feature migrations not yet installed. For production, use
`python manage.py collectstatic --noinput` and restart your usual Django service.

## Edit React

Use Node 22.12+ (tested with Node 24) and npm:

```sh
cd frontend
npm ci
npm run build
```

`npm run dev` runs Vite's **watch build**, writing the production assets on each
edit. Keep Django running in a second terminal and refresh its page after a
rebuild. There is intentionally no second browser origin, dev proxy, CORS setup
or separate Node process in production. This workflow does not offer HMR.
Commit source, lockfile, manifest and updated assets together.

```sh
npm test
cd ..
python manage.py test core.tests
python manage.py check
```

The asset filenames are content-hashed. Do not deploy source without its bundle,
and retain the repository's `static/react/.vite/manifest.json`: Django reads it
to resolve the current entry. The application process needs this local manifest;
static hosting/CDN only needs the emitted assets. Build before collectstatic.

## Architecture and contracts

React owns the rendered page and interactive state. Django keeps URL routing,
sessions, CSRF, permissions, localization, quiz grading, contest judging and AI
requests. Navigation and ordinary forms use the existing URLs and browser
requests. **This is a React multi-page frontend, not an SPA or React SSR.**
The landing page keeps its metadata but its body is client-rendered; SSR/SEO
prerendering can be introduced independently if needed.

`core.frontend.render_page` maps each authorized view context into explicitly
selected JSON props. `json_script` escapes HTML delimiters, preventing authored
titles from escaping the bootstrap script. It excludes credentials, judge test
inputs/outputs, lesson bodies other than the currently authorized lesson, and
quiz correctness flags before submission. Authenticated redirects/locking occur
before serialization. JSON requests (`Accept: application/json`) receive the
same envelope for future integrations; it includes a session CSRF token and
must not be cached. Responses set private/no-store and Vary: Accept.

`templates/react.html` is the sole React document shell; it loads no legacy
DOM-controller scripts. React uses the server translation dictionary, plus
explicit RU/KZ pairs for new labels. Date formatting uses Asia/Almaty.

Dynamic calls retain their contracts:

- Lead form: FormData → `lead_create`; validation and network errors stay visible.
- Quizzes: ordinary CSRF-protected form POST, `q_<question_id>` radio values.
- Contest: JSON → `contest_submit`; server owns the timing and verdict. Timer
  uses monotonic elapsed time, locks on expiry, and syncs to server remaining
  time after submission. Code drafts preserve the existing per-contest/account/
  task/language storage keys. Task switches are disabled during judging.
- BYTE AI: JSON `{message, history}` with CSRF and same-origin credentials.
  Replies are plain text; authored lesson/task HTML alone uses DOMPurify.
  Session history is additionally scoped by BYTE user ID to avoid restoring
  another student's chat after logging in on the same browser tab.
- Logout is POST-only on both Django 4.2 and 5.x.

The JS bundle is local, not fetched from a CDN. Fonts retain the existing Google
Fonts URLs. JavaScript is required for React pages; a bilingual noscript message
is provided. Existing Django templates and scripts remain for rollback:
set `REACT_FRONTEND_ENABLED=0` in `.env` and restart Django. This is a temporary
migration escape hatch; new features should be implemented in React.

## Validation

Backend tests cover both response formats, CSRF, login/logout, safe serialization,
RU/KZ, sequential unlock, quiz grading, contest data secrecy, AI route continuity
and fallback. Component tests cover form contracts, sanitization, language/theme
controls, chat, error states, draft persistence, contest submission/expiry and
Forecast edge cases. Browser smoke tests use a local demo account and database;
they do not modify the user's working database or production service.
