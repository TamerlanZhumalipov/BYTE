from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.legal import LEGAL_VERSION
from core.models import Lead, Section


class LegalTests(TestCase):
    def payload(self, **changes):
        return dict(name="Тестовый Пользователь", phone="+77000000000", plan="start",
                    privacy_consent="on", consent_version=LEGAL_VERSION, **changes)

    def test_pages_in_both_languages_and_public_navigation(self):
        for lang in ("ru", "kk"):
            session = self.client.session
            session["site_language"] = lang
            session.save()
            for page in ("index", "privacy", "terms", "cookies", "login"):
                response = self.client.get(reverse(page))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'lang="{lang}"')
                for target in ("privacy", "terms", "cookies"):
                    self.assertContains(response, f'href="{reverse(target)}"')
                self.assertNotContains(response, 'fonts.googleapis.com')
                self.assertContains(response, "tamush30@gmail.com") if page in ("privacy", "terms", "cookies") else None

    def test_missing_or_false_consent_does_not_save(self):
        for consent in (None, "", "false", "False"):
            data = self.payload()
            if consent is None:
                data.pop("privacy_consent")
            else:
                data["privacy_consent"] = consent
            response = self.client.post(reverse("lead_create"), data)
            self.assertEqual(response.status_code, 400)
            self.assertIn("privacy_consent", response.json()["errors"])
        self.assertEqual(Lead.objects.count(), 0)

    def test_consent_is_not_prechecked(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, 'type="checkbox" name="privacy_consent" value="on" required')
        self.assertNotContains(response, 'checked')

    def test_saves_server_evidence_without_operator_identifier(self):
        # The owner's explicit choice: no identifier gate on lead intake.
        with override_settings(BYTE_LEGAL={"operator": "Оператор", "identifier": "", "contact": "test@example.com", "location": "Казахстан"}):
            response = self.client.post(reverse("lead_create"), self.payload(consent_at="2000-01-01", consent_text="forged"))
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get()
        self.assertEqual(lead.consent_version, LEGAL_VERSION)
        self.assertEqual(lead.consent_language, "ru")
        self.assertGreater(lead.consent_at, timezone.now() - timedelta(minutes=1))
        self.assertIn("Оператор", lead.consent_text)
        self.assertNotIn("forged", lead.consent_text)

    def test_kazakh_consent_and_errors(self):
        session = self.client.session
        session["site_language"] = "kk"
        session.save()
        data = self.payload()
        data.pop("privacy_consent")
        self.assertIn("келісім", self.client.post(reverse("lead_create"), data).json()["errors"]["privacy_consent"][0])
        self.assertEqual(self.client.post(reverse("lead_create"), self.payload()).status_code, 200)
        lead = Lead.objects.get()
        self.assertEqual(lead.consent_language, "kk")
        self.assertIn("Өтінімді", lead.consent_text)

    def test_stale_or_missing_version_does_not_save(self):
        for version in (None, "old"):
            data = self.payload()
            if version is None:
                data.pop("consent_version")
            else:
                data["consent_version"] = version
            self.assertEqual(self.client.post(reverse("lead_create"), data).status_code, 400)
        self.assertFalse(Lead.objects.exists())

    def test_legacy_contact_alias_with_consent(self):
        data = self.payload()
        data["contact"] = data.pop("phone")
        self.assertEqual(self.client.post(reverse("lead_create"), data).status_code, 200)

    def test_csrf_still_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("lead_create"), self.payload()).status_code, 403)

    def test_existing_lead_has_no_invented_consent(self):
        lead = Lead.objects.create(name="Legacy", phone="test")
        self.assertIsNone(lead.consent_at)
        self.assertEqual(lead.consent_text, "")

    def test_video_is_inert_before_browser_consent(self):
        user = User.objects.create_user("student", password="test-only-password")
        self.client.force_login(user)
        section = Section.objects.create(title="Видео", slug="video", video_url="https://www.youtube.com/watch?v=example")
        response = self.client.get(reverse("section", args=[section.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-external-video="https://www.youtube.com/embed/example"')
        self.assertNotContains(response, '<iframe')

    def test_retention_dry_run_and_deletion(self):
        old = Lead.objects.create(name="Expired", phone="test")
        fresh = Lead.objects.create(name="Current", phone="test")
        Lead.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=91))
        call_command("purge_expired_leads", stdout=StringIO())
        self.assertTrue(Lead.objects.filter(pk=old.pk).exists())
        call_command("purge_expired_leads", "--delete", stdout=StringIO())
        self.assertFalse(Lead.objects.filter(pk=old.pk).exists())
        self.assertTrue(Lead.objects.filter(pk=fresh.pk).exists())
