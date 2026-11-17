from django.test import SimpleTestCase
from django.urls import resolve


class AdminDeploymentRoutingTests(SimpleTestCase):
    def test_django_admin_root_is_mounted(self):
        match = resolve("/admin/")

        self.assertEqual(match.namespace, "admin")

    def test_custom_admin_login_route_is_preserved(self):
        match = resolve("/admin/login/")

        self.assertEqual(match.url_name, "admin_login")
