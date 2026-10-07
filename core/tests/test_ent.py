from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.ent import get_ent_catalogue
from core.models import ENTSpecification, ENTTopic, Section, TopicQuiz, QuizAttempt
from core.views import _build_tree, _decorate_learning_path


class ENTTests(TestCase):
    def setUp(self):
        self.spec = ENTSpecification.objects.get(year=2026)
        self.user = get_user_model().objects.create_user(username="learner", password="secret")

    def seed(self):
        import_module("core.migrations.0005_seed_ent_2026").seed(
            apps, SimpleNamespace(connection=connection), map_existing=True,
        )

    def test_catalogue_and_unique_codes(self):
        topics = list(self.spec.topics.all())
        self.assertEqual([t.code for t in topics], [f"{i:02}" for i in range(1, 14)])
        self.assertTrue(all(t.title and t.title_kk for t in topics))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ENTTopic.objects.create(specification=self.spec, code="01", title="duplicate")

    def test_seed_real_roots_idempotent_and_preserves_edits(self):
        call_command("seed_materials", verbosity=0)
        self.seed()
        self.assertEqual(self.spec.topics.get(code="03").sections.count(), 3)
        self.assertEqual(set(self.spec.topics.get(code="07").sections.values_list("slug", flat=True)), {"python", "datastructs"})
        self.assertFalse(self.spec.topics.get(code="11").sections.exists())
        self.assertFalse(Section.objects.get(slug="cpp").ent_topics.exists())
        topic = self.spec.topics.get(code="01")
        topic.title = "Edited"
        topic.save()
        topic.sections.clear()
        call_command("seed_ent_specification", verbosity=0)
        topic.refresh_from_db()
        self.assertEqual(topic.title, "Edited")
        self.assertFalse(topic.sections.exists())
        self.seed()
        self.seed()
        self.assertEqual(topic.sections.count(), 1)

    def test_matching_by_title_avoids_children_and_ambiguity(self):
        root = Section.objects.create(title="  СИСТЕМЫ   СЧИСЛЕНИЯ ", slug="renamed")
        Section.objects.create(title="Системы счисления", slug="numbers", parent=root)
        self.seed()
        self.assertEqual(list(self.spec.topics.get(code="04").sections.all()), [root])
        self.spec.topics.get(code="04").sections.clear()
        Section.objects.create(title="Системы счисления", slug="duplicate-title")
        self.seed()
        self.assertFalse(self.spec.topics.get(code="04").sections.exists())

    def test_api_auth_languages_missing_and_get_only(self):
        url = reverse("ent_specification", args=[2026])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        session = self.client.session
        session["site_language"] = "kk"
        session.save()
        data = self.client.get(url).json()
        self.assertEqual(data["topics"][0]["title"], "Компьютердің құрылғылары")
        self.assertEqual(self.client.get(url, {"language": "ru"}).json()["language"], "ru")
        self.assertEqual(self.client.get(url, {"language": "kz"}).json()["language"], "kk")
        self.assertEqual(self.client.get(url, {"language": "en"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("ent_specification", args=[2030])).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 405)

    def test_service_filters_hidden_sections_and_falls_back(self):
        topic = self.spec.topics.get(code="01")
        topic.title_kk = ""
        topic.save()
        topic.sections.add(Section.objects.create(title="Hidden", slug="hidden", is_published=False))
        with self.assertNumQueries(3):
            data = get_ent_catalogue(language="kk")
        self.assertEqual(data["topics"][0]["title"], topic.title)
        self.assertEqual(data["topics"][0]["sections"], [])

    def test_learning_path_quizzes_and_analytics_unchanged(self):
        first = Section.objects.create(title="First", title_kk="Бірінші", slug="first", order=1)
        second = Section.objects.create(title="Second", slug="second", order=2)
        quiz = TopicQuiz.objects.create(topic=first)
        self.spec.topics.get(code="01").sections.add(first, second)
        roots, _ = _build_tree("kk")
        _decorate_learning_path(self.user, roots)
        self.assertEqual([r.is_locked for r in roots], [False, True])
        QuizAttempt.objects.create(user=self.user, quiz=quiz, score_percent=100, correct_count=1, total_questions=1, passed=True)
        _decorate_learning_path(self.user, roots)
        self.assertEqual([r.is_locked for r in roots], [False, False])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("analytics")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
