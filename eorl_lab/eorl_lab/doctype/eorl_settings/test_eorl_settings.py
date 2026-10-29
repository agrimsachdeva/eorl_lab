import frappe
from frappe.tests.utils import FrappeTestCase


class TestEORLSettings(FrappeTestCase):
	def test_singleton_accessible(self):
		settings = frappe.get_single("EORL Settings")
		self.assertEqual(settings.doctype, "EORL Settings")
