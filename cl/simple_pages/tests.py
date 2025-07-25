from http import HTTPStatus
from typing import Any, cast
from unittest.mock import MagicMock, patch

from asgiref.sync import sync_to_async
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from lxml.html import fromstring

from cl.audio.factories import AudioWithParentsFactory
from cl.lib.test_helpers import SimpleUserDataMixin
from cl.tests.cases import TestCase


# Mock the hcaptcha thing so that we're sure it validates during tests
@patch("hcaptcha.fields.hCaptchaField.validate", return_value=True)
class ContactTest(SimpleUserDataMixin, TestCase):
    test_msg = {
        "name": "pandora",
        "phone_number": "asdf",
        "issue_type": "support",
        "message": "123456789012345678901",
        "email": "pandora@box.com",
        "hcaptcha": "xxx",
    }

    async def test_multiple_requests_request(self, mock: MagicMock) -> None:
        """Is state persisted in the contact form?

        The contact form is abstracted in a way that it can have peculiar
        behavior when called multiple times. This test makes sure that that
        behavior does not regress.
        """
        self.assertTrue(
            await self.async_client.alogin(
                username="pandora", password="password"
            )
        )
        await self.async_client.get(reverse("contact"))
        await self.async_client.alogout()

        # Now, as an anonymous user, we get the page again. If the bug is
        # resolved, we should not see anything about the previously logged-in
        # user, pandora.
        r = await self.async_client.get(reverse("contact"))
        self.assertNotIn("pandora", r.content.decode())

    async def test_contact_logged_in(self, mock: MagicMock) -> None:
        """Can we use the contact form to send a message when logged in?"""
        self.assertTrue(
            await self.async_client.alogin(
                username="pandora", password="password"
            )
        )
        response = await self.async_client.post(
            reverse("contact"), self.test_msg
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(len(mail.outbox), 1)

    async def test_contact_logged_out(self, mock: MagicMock) -> None:
        """Can we use the contact form to send a message when logged out?"""
        response = await self.async_client.post(
            reverse("contact"), self.test_msg
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(len(mail.outbox), 1)

    async def test_contact_unicode(self, mock: MagicMock) -> None:
        """Can unicode be used when contacting us?"""
        msg = self.test_msg.copy()
        msg["message"] = (
            "Possible ideas and thoughts are vast in number. A distinct word "
            "for every distinct idea and thought would require a vast "
            "vocabulary. The problem in language is to express many ideas and "
            "thoughts with comparatively few words. — John Wesley Powell"
        )
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(len(mail.outbox), 1)

    async def test_spam_message_is_rejected(self, mock: MagicMock) -> None:
        """Do we reject it if people put a phone number in the phone_number
        field?

        We should! The phone_number field is labeled as the Subject field in the
        UI. Anything putting a phone number in here is a bot to be rejected.
        """
        msg = self.test_msg.copy()
        msg["phone_number"] = "909-576-4123"
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(len(mail.outbox), 0)

        # Number in middle of subject is OK!
        msg["phone_number"] = "asdf 909 asdf"
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(len(mail.outbox), 1)

    async def test_removals_require_http(self, mock: MagicMock) -> None:
        """Do we ensure removals have an HTTP link?"""
        msg = self.test_msg.copy()

        # Removal subject without link fails
        msg["phone_number"] = "Removal request"
        msg["message"] = "test in message with lots of long words"
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(mail.outbox), 0)

        msg["phone_number"] = "Please remove link!"
        msg["message"] = "test in message with lots of long words"
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(mail.outbox), 0)

        # Test regex matching on removals fails
        msg["phone_number"] = "take down request"
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(mail.outbox), 0)

        # Removal subject with link is OK!
        msg["message"] = "test http in message"
        response = await self.async_client.post(reverse("contact"), msg)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(len(mail.outbox), 1)


class SimplePagesTest(SimpleUserDataMixin, TestCase):
    def assert_page_title_in_html(self, content: str) -> None:
        """Make sure a page has a valid HTML title"""
        print("Checking for HTML title tag....", end="")
        html_tree = fromstring(content)
        title = cast(list[str], html_tree.xpath("//title/text()"))
        self.assertGreater(
            len(title),
            0,
            msg="This page didn't have any text in it's <title> tag.",
        )
        self.assertGreater(
            len(title[0].strip()),
            0,
            msg="The text in this title tag is empty.",
        )
        print("✓")

    async def assert_page_loads_ok(self, reverse_param: dict) -> None:
        """Does a page load properly?

        :param reverse_param: Params that can be sent to Django's reverse
        function to get a URL path.
        :return: None
        """
        path = reverse(**reverse_param)
        print(f"Testing basic load of: {path}...", end="")
        r = await self.async_client.get(path)
        self.assertEqual(
            r.status_code,
            HTTPStatus.OK,
            msg="Got wrong status code for page at: {path}\n  args: "
            "{args}\n  kwargs: {kwargs}\n  Status Code: {code}".format(
                path=path,
                args=reverse_param.get("args", []),
                kwargs=reverse_param.get("kwargs", {}),
                code=r.status_code,
            ),
        )
        print("✓")
        is_html = "text/html" in r["content-type"]
        if r["content-type"] and is_html:
            self.assert_page_title_in_html(r.content)

    async def test_simple_pages(self) -> None:
        """Do all the simple pages load properly?"""
        reverse_params: list[dict[str, Any]] = [
            # Coverage
            {"viewname": "coverage"},
            {"viewname": "coverage_fds"},
            {"viewname": "coverage_recap"},
            {"viewname": "coverage_oa"},
            # Info pages
            {"viewname": "faq"},
            {"viewname": "feeds_info"},
            {"viewname": "contribute"},
            {"viewname": "replication_docs"},
            {"viewname": "terms"},
            {"viewname": "robots"},
            # Contact
            {"viewname": "contact"},
            {"viewname": "contact_thanks"},
            # Help pages
            {"viewname": "help_home"},
            {"viewname": "alert_help"},
            {"viewname": "delete_help"},
            {"viewname": "markdown_help"},
            {"viewname": "advanced_search"},
            {"viewname": "recap_email_help"},
            {"viewname": "broken_email_help"},
            # API help pages
            {"viewname": "case_law_api_help"},
            {"viewname": "citation_api_help"},
            {"viewname": "pacer_api_help"},
            {"viewname": "recap_api_help"},
            {"viewname": "judge_api_help"},
            {"viewname": "field_api_help"},
            {"viewname": "oral_argument_api_help"},
            {"viewname": "visualization_api_help"},
            {"viewname": "webhooks_docs"},
            {"viewname": "webhooks_getting_started"},
            {"viewname": "citation_lookup_api"},
            {"viewname": "alert_api_help"},
            {"viewname": "financial_disclosures_api_help"},
            {"viewname": "search_api_help"},
            {"viewname": "rest_change_log"},
            {"viewname": "old_terms", "args": ["1"]},
            {"viewname": "old_terms", "args": ["2"]},
            # Monitoring pages
            {"viewname": "celery_queue_lengths"},
            {"viewname": "heartbeat"},
            {"viewname": "health_check"},
            {"viewname": "check_redis_writes"},
            {"viewname": "elastic_status"},
            {"viewname": "replication_status"},
        ]
        for reverse_param in reverse_params:
            with self.subTest(
                "Checking simple pages", reverse_params=reverse_param
            ):
                await self.assert_page_loads_ok(reverse_param)

    async def test_profile_urls(self) -> None:
        """Do all of the profile URLs load properly?"""
        self.assertTrue(
            await self.async_client.alogin(
                username="pandora", password="password"
            )
        )
        reverse_params = [
            {"viewname": "view_settings"},
            {"viewname": "profile_notes"},
            {"viewname": "profile_search_alerts"},
            {"viewname": "profile_docket_alerts"},
            {"viewname": "view_visualizations"},
            {"viewname": "view_deleted_visualizations"},
            {"viewname": "password_change"},
            {"viewname": "delete_account"},
            {"viewname": "take_out"},
            {"viewname": "profile_your_support"},
            {"viewname": "view_api"},
        ]
        for reverse_param in reverse_params:
            await self.assert_page_loads_ok(reverse_param)

    async def test_oa_minute_count_in_the_coverage_page(self) -> None:
        "is the minute count rounded in the coverage page?"
        cache.delete("coverage-data-v3")
        await sync_to_async(AudioWithParentsFactory)(duration=250)
        r = await self.async_client.get(reverse("coverage"))
        self.assertIn("4 minutes of recordings.", r.content.decode())
        self.assertIn(
            "with 4 minutes of recordings (and counting).", r.content.decode()
        )
