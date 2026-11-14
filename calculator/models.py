from django.db import models
from django.utils import timezone
from .calculator_engine import compute_rate_card, MARGIN_TIERS


class RateCalculation(models.Model):
    date = models.DateField(default=timezone.now, help_text="Calculation date")
    product = models.CharField(max_length=120, help_text="e.g. JINDAL, Sakthi, Duramet")
    thickness = models.DecimalField(max_digits=6, decimal_places=2, help_text="Thickness in mm (e.g. 0.35, 2.30)")
    weight_10ft = models.FloatField(help_text="Weight of a 10-feet sheet in kg (e.g. 8.4)")
    landing_rate = models.FloatField(help_text="Basic purchase rate per kg in INR (excl. GST)")
    is_gst_included = models.BooleanField(
        default=False,
        help_text="Always False (basic rate excludes 18% GST)"
    )

    # Calculated intermediate metrics
    rate_incl_gst = models.FloatField(help_text="Effective landing rate per kg incl. GST")
    ton_rate = models.FloatField(help_text="Rate per Metric Ton (1000 kg)")
    sheets_per_ton = models.FloatField(help_text="Estimated 10ft sheets per Ton")
    sqft_per_ton = models.FloatField(help_text="Total Sq. Ft coverage per Ton")
    cost_per_sqft = models.FloatField(help_text="Base cost per Sq. Ft")

    # Calculated Selling Rate Tiers (Margin per kg: 15, 13, 11, 10, 8, 7, 6, 5, 4, 3)
    tier_15 = models.FloatField(null=True, blank=True)
    tier_13 = models.FloatField(null=True, blank=True)
    tier_11 = models.FloatField(null=True, blank=True)
    tier_10 = models.FloatField(null=True, blank=True)
    tier_8 = models.FloatField(null=True, blank=True)
    tier_7 = models.FloatField(null=True, blank=True)
    tier_6 = models.FloatField(null=True, blank=True)
    tier_5 = models.FloatField(null=True, blank=True)
    tier_4 = models.FloatField(null=True, blank=True)
    tier_3 = models.FloatField(null=True, blank=True)

    tier_rates = models.JSONField(default=dict, blank=True, help_text="Map of margin to selling price per sqft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Rate Calculation'
        verbose_name_plural = 'Rate Calculations'

    def __str__(self):
        return f"{self.product} - {self.thickness}mm ({self.date})"

    def save(self, *args, **kwargs):
        # Auto-compute if not filled
        results = compute_rate_card(
            landing_rate=self.landing_rate,
            weight_10ft=self.weight_10ft
        )
        self.rate_incl_gst = results['rate_incl_gst']
        self.ton_rate = results['ton_rate']
        self.sheets_per_ton = results['sheets_per_ton']
        self.sqft_per_ton = results['sqft_per_ton']
        self.cost_per_sqft = results['cost_per_sqft']
        self.tier_rates = results['tier_rates']

        # Populate individual tier columns
        self.tier_15 = results['tier_rates'].get('15')
        self.tier_13 = results['tier_rates'].get('13')
        self.tier_11 = results['tier_rates'].get('11')
        self.tier_10 = results['tier_rates'].get('10')
        self.tier_8 = results['tier_rates'].get('8')
        self.tier_7 = results['tier_rates'].get('7')
        self.tier_6 = results['tier_rates'].get('6')
        self.tier_5 = results['tier_rates'].get('5')
        self.tier_4 = results['tier_rates'].get('4')
        self.tier_3 = results['tier_rates'].get('3')

        super().save(*args, **kwargs)

    @property
    def formatted_date(self):
        return self.date.strftime("%d-%b-%Y") if self.date else ""

    def get_tier_list(self):
        """Returns structured list for rendering grids in templates"""
        tiers = []
        for m in MARGIN_TIERS:
            val = self.tier_rates.get(str(m)) or getattr(self, f"tier_{m}", 0.0)
            tiers.append({
                'margin': m,
                'rate': val
            })
        return tiers
