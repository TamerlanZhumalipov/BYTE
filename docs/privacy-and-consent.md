# BYTE: privacy, terms and consent

Implemented on 26 October 2026. Applies to the repository's Django site; deployed infrastructure, proxy logs, third-party account settings and the operator's business processes were not independently inspected.

## Pages and behaviour

- `/privacy/`, `/terms/`, `/cookies/`: Russian and Kazakh, public without login, links on the landing page, login and app pages.
- Lead form: one required, initially unchecked consent checkbox; full consent visible inline and linked. Server rejects absent/false consent and missing/stale document version. Existing `contact` alias remains supported with consent.
- Each new lead stores server timestamp, document version, language and rendered consent text. The submitted name/contact remain in the lead. No extra IP or browser fingerprint is collected as consent evidence. This records the form action, not independently verified identity.
- Old leads keep blank evidence. Admin exposes consent fields read-only. Existing records must not be treated as newly consented.
- Intake remains enabled without an operator identifier, as explicitly requested by the owner. No identifiers have been invented or included in Git. Optional `BYTE_LEGAL_IDENTIFIER` is displayed in consent if the operator later configures it; it is not secret once shown to visitors.
- Owner supplied: Жумалипов Тамерлан Айдарович; tamush30@gmail.com; Kazakhstan hosting. Exact hosting provider and backup location still require confirmation by the operator.
- The lead form requests the sender's full name and their own contact; a note asks under-18s to have a parent submit their own details. This is not a verified parental-consent workflow for enrolment.

## Legal assessment and unresolved scope

Official sources checked on 26 October 2026:

1. [Kazakhstan Law on Personal Data, Articles 7–8, 12 and 16](https://old.adilet.zan.kz/rus/docs/Z1300000094).
2. [Rules for collection and processing, including 2026 amendments](https://old.adilet.zan.kz/rus/docs/V2000021498).

For this contact form, obtain consent before collecting personal data, make the purpose/data/recipient/period visible, and retain evidence. A checkbox plus server record is the implemented confirmation mechanism. It is not an electronic signature or proof of the person's identity.

Article 8 lists the operator's IIN/BIN as part of consent. The owner declined to provide it and explicitly requested continued lead intake. The implementation honours that instruction; **the consent without that requisite should not be represented as fully compliant**. The operator should resolve the requisite/disclosure approach with a Kazakhstan lawyer; no frontend setting can cure that documentary gap.

The reviewed Kazakhstan provisions do not establish a standalone EU-style requirement for a banner for every technical cookie. Necessary session/CSRF storage is documented. Optional external video is blocked before permission as a conservative implementation where device data may be transferred. This is not a general exemption from personal-data obligations, and no GDPR applicability assessment was made for an EU-targeted service.

The privacy page documents existing AI storage and Gemini transmission; it does not create a new consent workflow for existing student accounts, AI or public contest rankings. Before enrolling children or using those functions, establish the appropriate enrolment/representative and data-transfer permissions. This change does not certify the entire platform's compliance. The named contact uses Gmail; external processing is disclosed. The local database country was supplied by the owner, not verified from code.

## Browser audit

No Google Analytics, Yandex Metrika or advertising pixels were found in the checked templates/scripts. Google Fonts requests were removed from the three base documents so public pages do not automatically contact Google for typography; system fallback fonts are used.

| Storage | Purpose | Lifetime |
| --- | --- | --- |
| Django CSRF cookie | Form integrity | Runtime `CSRF_COOKIE_AGE` (default 364 days) |
| Django session cookie | Login, language and contest session | Runtime `SESSION_COOKIE_AGE` (default 14 days) |
| `byte-theme` | Requested theme | Until browser storage is cleared |
| `byte:…` | Contest draft/editor preferences | Until browser storage is cleared |
| `byte-ai-session:…` | Current-tab AI dialogue | Session storage |
| `byte-privacy-choice` | Optional-media decision/version/time | 180 days; expired entries removed on access |

Lesson iframe URLs are inert data attributes until optional-media permission. Denial/removal closes loaded frames; expired, invalid or old-version choices default to no media. Choice is local to the browser, not a central consent register. Disabling JavaScript prevents embeds entirely. Storage errors do not break basic UI. Existing provider cookies cannot be erased by BYTE. Editors must not bypass this mechanism by inserting active third-party iframes/scripts directly into lesson HTML. Any added analytics, pixels or embeds require a new audit and consent integration.

## Deployment

1. Apply migrations: `python manage.py migrate` (0009 adds nullable/blank consent evidence; no historical consent is backfilled).
2. Collect static assets and restart the application using the existing deployment process. Deploy templates, code and migration together.
3. Optional operator values use `BYTE_LEGAL_OPERATOR`, `BYTE_LEGAL_CONTACT`, `BYTE_LEGAL_LOCATION`, `BYTE_LEGAL_IDENTIFIER` after `.env` loading. The first three default to owner-provided values. Do not commit private identifiers or `.env`.
4. On every substantive change to consent or operator details, bump `LEGAL_VERSION` in `core/legal.py`. Keep previous versions in Git and per-lead snapshots; the API rejects stale forms.
5. The proposed maximum lead retention is 90 days. Schedule `python manage.py purge_expired_leads --delete` at least daily on the deployment host. Without `--delete`, it only reports the count. Arrange earlier deletion on completion/withdrawal and matching backup expiry. **The scheduler has not been installed by this change.** Do not publish a retention promise without operationalising it. Enrolment uses a separate basis/record, not indefinite storage of the sales lead.
6. Handle deletion/withdrawal requests received by email and verify sender identity proportionately. Define access rights and backup retention with the actual hosting provider.

## Verification

- Django: full `core.tests` suite, including public pages in both languages, required consent, stale version, server-generated evidence, existing records, CSRF, inert video and retention dry-run/deletion.
- Browser: actual form submission with/without consent; desktop/mobile light/dark rendering; RU/KZ switch; no external requests before permission; allow, revoke, reload, expiration, invalid storage and storage-disabled behaviour.
- No production data was accessed or migrated; preview uses an isolated test database.
