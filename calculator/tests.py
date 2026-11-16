from django.test import TestCase, Client
from django.urls import reverse
from .models import RateCalculation
from .calculator_engine import compute_rate_card, MARGIN_TIERS


class CalculationEngineTest(TestCase):
    def test_calculation_with_basic_rate_excluding_gst(self):
        # landing_rate = 75.0 (basic rate excl. GST), 18% GST automatically added
        res = compute_rate_card(landing_rate=75.0, weight_10ft=8.4)
        self.assertEqual(res['rate_incl_gst'], 88.50)
        self.assertEqual(res['ton_rate'], 88500.0)
        self.assertEqual(res['sheets_per_ton'], 119.05)
        self.assertEqual(res['sqft_per_ton'], 4285.71)
        self.assertEqual(res['cost_per_sqft'], 20.65)

        # Margin 15: (88500 + 15000) / (1000 / 8.4 * 36) = 103500 / 4285.71428 = 24.15
        self.assertEqual(res['tier_rates']['15'], 24.15)
        self.assertEqual(res['tier_rates']['10'], 22.98)
        self.assertEqual(res['tier_rates']['3'], 21.35)


class RateCalculationModelTest(TestCase):
    def test_model_save_and_auto_computation(self):
        calc = RateCalculation.objects.create(
            product="JINDAL",
            thickness=0.35,
            weight_10ft=8.4,
            landing_rate=75.0
        )
        self.assertEqual(calc.rate_incl_gst, 88.50)
        self.assertEqual(calc.tier_15, 24.15)
        self.assertEqual(calc.tier_3, 21.35)
        self.assertIn("15", calc.tier_rates)
        self.assertEqual(len(calc.get_tier_list()), 10)


class ViewsAndApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.calc = RateCalculation.objects.create(
            product="Sakthi",
            thickness=0.45,
            weight_10ft=10.5,
            landing_rate=80.0
        )

    def test_dashboard_renders(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Roofing Margin & Rate Card")
        self.assertContains(response, "Sakthi")
        # Ensure GST toggle is NOT present in the page
        self.assertNotContains(response, 'id="input-is-gst"')

    def test_search_filter(self):
        response = self.client.get(reverse('dashboard') + '?search=Sakthi')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sakthi")

        response_empty = self.client.get(reverse('dashboard') + '?search=NonExistentBrand')
        self.assertEqual(response_empty.status_code, 200)
        self.assertNotContains(response_empty, "history-row-" + str(self.calc.id))

    def test_calculate_api(self):
        response = self.client.post(
            reverse('api_calculate'),
            data={'landing_rate': 75.0, 'weight_10ft': 8.4}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['rate_incl_gst'], 88.5)

    def test_get_calculation_api(self):
        response = self.client.get(reverse('api_get_calculation', args=[self.calc.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['product'], 'Sakthi')

    def test_delete_calculation(self):
        response = self.client.post(reverse('delete_calculation', args=[self.calc.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(RateCalculation.objects.filter(pk=self.calc.id).exists())

    def test_dashboard_post_saves_calculation_automatically(self):
        initial_count = RateCalculation.objects.count()
        response = self.client.post(reverse('dashboard'), data={
            'product': 'Duramet Test',
            'thickness': '0.40',
            'weight_10ft': '9.25',
            'landing_rate': '82.50',
            'date': '2026-11-14',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RateCalculation.objects.count(), initial_count + 1)
        saved = RateCalculation.objects.get(product='Duramet Test')
        self.assertEqual(float(saved.thickness), 0.40)
        self.assertEqual(saved.weight_10ft, 9.25)

    def test_pwa_manifest_json(self):
        response = self.client.get(reverse('pwa_manifest'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        data = response.json()
        self.assertEqual(data['name'], 'Roofing Margin & Rate Card Calculator')
        self.assertEqual(data['display'], 'standalone')

    def test_pwa_service_worker(self):
        response = self.client.get(reverse('pwa_sw'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertIn('roofing-calc', response.content.decode('utf-8'))

    def test_dashboard_post_preserves_trailing_zeros(self):
        response = self.client.post(reverse('dashboard'), data={
            'product': 'TrailingZero Test',
            'thickness': '0.35',
            'weight_10ft': '8.450',
            'landing_rate': '75.00',
            'date': '2026-11-16',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('w=8.450', response.url)
        # Follow redirect and verify 8.450 is rendered in the card and form
        follow_resp = self.client.get(response.url)
        self.assertEqual(follow_resp.status_code, 200)
        self.assertContains(follow_resp, '8.450')

    def test_favicon_ico_view(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/x-icon')
        self.assertGreater(len(response.content), 0)
