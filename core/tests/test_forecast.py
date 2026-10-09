from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.forecast import get_forecast
from core.models import (ENTSpecification, ENTTopic, ENTPracticeResult, Section,
                         TopicQuiz, QuizAttempt, Contest, ContestTask, ContestAccount, Submission)


class ForecastTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(username="student")
        self.other = get_user_model().objects.create_user(username="other")
        self.spec = ENTSpecification.objects.get(year=2026)
        self.topics = list(self.spec.topics.all())
        self.sections = []
        for i, topic in enumerate(self.topics):
            section = Section.objects.create(title=f"Topic {i}", slug=f"topic-{i}", order=i)
            topic.sections.add(section)
            self.sections.append(section)

    def attempt(self, index=0, correct=8, total=10, days=0, user=None):
        quiz, _ = TopicQuiz.objects.get_or_create(topic=self.sections[index])
        attempt = QuizAttempt.objects.create(user=user or self.user, quiz=quiz, correct_count=correct,
                                            total_questions=total, score_percent=round(correct/total*100) if total else 0,
                                            passed=bool(total and correct/total >= .7))
        QuizAttempt.objects.filter(pk=attempt.pk).update(created_at=self.now-timedelta(days=days))
        return attempt

    def mock(self, score=40, days=0, verified=True, user=None, reference="mock-1"):
        return ENTPracticeResult.objects.create(user=user or self.user, specification=self.spec,
            score=score, max_score=50, taken_at=self.now-timedelta(days=days), source="Full mock",
            verified=verified, reference=reference)

    def forecast(self):
        return get_forecast(self.user, now=self.now)

    def test_empty_and_single_quiz_do_not_predict_exam(self):
        self.assertIsNone(self.forecast()["score"])
        self.attempt(correct=10)
        data = self.forecast()
        self.assertEqual(data["status"], "insufficient_data")
        self.assertIsNone(data["score"])
        self.assertIsNone(data["topics"][1]["mastery"])
        self.assertLess(data["topics"][0]["mastery"], 100)

    def test_multiple_topics_bounds_and_confidence(self):
        for i in range(8):
            self.attempt(i, correct=10)
        data = self.forecast()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(0 <= data["low"] <= data["score"] <= data["high"] <= 50)
        self.assertEqual(data["confidence"], "low")
        self.assertEqual(data["quiz_count"], 8)
        self.assertIsNone(data["delta"])

    def test_retries_do_not_inflate_evidence(self):
        self.attempt()
        before = self.forecast()
        for _ in range(20):
            self.attempt()
        after = self.forecast()
        self.assertEqual(after["coverage_percent"], before["coverage_percent"])
        self.assertEqual(after["quiz_count"], 1)
        self.assertIsNone(after["score"])

    def test_recent_failure_reduces_mastery(self):
        self.attempt(correct=10, days=2)
        before = self.forecast()["topics"][0]["mastery"]
        self.attempt(correct=0)
        self.assertLess(self.forecast()["topics"][0]["mastery"], before)

    def test_shared_mapping_does_not_duplicate_evidence(self):
        self.attempt(correct=10)
        single = self.forecast()["topics"][0]["coverage"]
        self.topics[1].sections.add(self.sections[0])
        data = self.forecast()
        self.assertEqual(data["quiz_count"], 1)
        self.assertLess(data["topics"][0]["coverage"], single)
        self.assertIsNone(data["score"])

    def test_stale_invalid_and_future_attempts_excluded(self):
        self.attempt(0, days=181)
        self.attempt(1, days=-1)
        self.attempt(2, correct=0, total=0)
        data = self.forecast()
        self.assertEqual(data["quiz_count"], 0)

    def test_mock_produces_estimate_without_inventing_topic_mastery(self):
        self.mock(score=42)
        data = self.forecast()
        self.assertEqual(data["score"], 42)
        self.assertEqual(data["mock_count"], 1)
        self.assertTrue(all(t["mastery"] is None for t in data["topics"]))
        self.assertEqual(data["coverage_percent"], 0)
        self.assertLess(data["low"], data["high"])

    def test_unverified_stale_future_and_other_user_mocks_excluded(self):
        self.mock(verified=False)
        self.mock(days=91, reference="old")
        self.mock(days=-1, reference="future")
        self.mock(user=self.other, reference="other")
        self.assertIsNone(self.forecast()["score"])

    def test_historical_forecast_excludes_future_evidence(self):
        self.mock(score=20, days=31)
        self.mock(score=45, reference="new")
        data = self.forecast()
        self.assertEqual(data["history"][0]["score"], 20)
        self.assertGreater(data["score"], 20)
        self.assertEqual(data["delta"], data["score"]-20)
        self.assertEqual(data["confidence"], "low")

    def test_user_results_isolated(self):
        for i in range(13):
            self.attempt(i, user=self.other)
        self.assertEqual(self.forecast()["quiz_count"], 0)

    def test_contest_requires_explicit_user_and_topic_links(self):
        contest = Contest.objects.create(title="Contest", starts_at=self.now)
        task = ContestTask.objects.create(contest=contest, title="Task", statement="...")
        task.ent_topics.add(self.topics[0])
        account = ContestAccount.objects.create(contest=contest, login="student")
        sub = Submission.objects.create(account=account, task=task, code="", language="python", verdict="OK", passed=10, total=10)
        Submission.objects.filter(pk=sub.pk).update(created_at=self.now)
        self.assertEqual(self.forecast()["contest_count"], 0)
        account.user = self.user
        account.save()
        self.assertEqual(self.forecast()["contest_count"], 1)
        task.ent_topics.clear()
        self.assertEqual(self.forecast()["contest_count"], 0)

    def test_missing_specification_graceful(self):
        self.spec.delete()
        self.assertEqual(self.forecast()["status"], "unavailable")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("analytics")).status_code, 200)

    def test_api_private_get_only_and_ignores_other_user_id(self):
        url = reverse("ent_forecast")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.mock(user=self.other)
        self.client.force_login(self.user)
        response = self.client.get(url, {"user_id": self.other.pk, "language": "kz"})
        self.assertIsNone(response.json()["score"])
        self.assertEqual(response.json()["language"], "kk")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(url, {"language": "bad"}).status_code, 400)

    def test_ru_kz_render_and_no_network_needed(self):
        self.client.force_login(self.user)
        self.mock()
        self.assertContains(self.client.get(reverse("analytics")), "Если сдавать ЕНТ сегодня")
        session = self.client.session
        session["site_language"] = "kk"
        session.save()
        response = self.client.get(reverse("analytics"))
        self.assertContains(response, "ҰБТ-ны бүгін тапсырсаңыз")
        self.assertNotContains(response, "Как считается прогноз")

    def test_mock_validation_and_duplicate_reference(self):
        result = self.mock()
        result.score = 51
        with self.assertRaises(ValidationError):
            result.full_clean()
        result.score = 20
        result.taken_at = self.now + timedelta(days=1)
        with self.assertRaises(ValidationError):
            result.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.mock()

    def test_query_count_bounded_with_evidence(self):
        for i in range(13):
            self.attempt(i)
        with self.assertNumQueries(6):
            self.forecast()

    def test_two_recent_mocks_allow_medium_reliability(self):
        self.mock(days=2)
        self.mock(days=1, reference="recent-2")
        self.assertEqual(self.forecast()["confidence"], "medium")

    def test_zero_mock_score_is_a_valid_result(self):
        self.mock(score=0)
        data = self.forecast()
        self.assertEqual(data["score"], 0)
        self.assertEqual(data["low"], 0)
        self.assertGreater(data["high"], 0)

    def test_contest_retries_pending_and_foreign_users(self):
        contest = Contest.objects.create(title="Contest", starts_at=self.now)
        task = ContestTask.objects.create(contest=contest, title="Task", statement="...")
        task.ent_topics.add(self.topics[0], self.topics[1])
        account = ContestAccount.objects.create(contest=contest, login="owner", user=self.user)
        foreign = ContestAccount.objects.create(contest=contest, login="foreign", user=self.other)
        for account_obj, verdict, passed in [(account, "OK", 10), (account, "WA", 0), (account, "PENDING", 10), (foreign, "OK", 10)]:
            sub = Submission.objects.create(account=account_obj, task=task, code="", language="python", verdict=verdict, passed=passed, total=10)
            Submission.objects.filter(pk=sub.pk).update(created_at=self.now)
        with self.assertNumQueries(7):
            data = self.forecast()
        self.assertEqual(data["contest_count"], 1)
        self.assertLess(data["topics"][0]["mastery"], 50)

    def test_unknown_topic_has_no_api_point_estimate(self):
        self.assertIsNone(self.forecast()["topics"][0]["model_points"])
