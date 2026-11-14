from django.contrib import admin
from .models import RateCalculation


@admin.register(RateCalculation)
class RateCalculationAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'thickness',
        'date',
        'weight_10ft',
        'landing_rate',
        'rate_incl_gst',
        'cost_per_sqft',
        'tier_15',
        'tier_3',
        'created_at'
    )
    list_filter = ('product', 'date', 'is_gst_included')
    search_fields = ('product',)
    date_hierarchy = 'date'
    readonly_fields = (
        'rate_incl_gst',
        'ton_rate',
        'sheets_per_ton',
        'sqft_per_ton',
        'cost_per_sqft',
        'tier_15',
        'tier_13',
        'tier_11',
        'tier_10',
        'tier_8',
        'tier_7',
        'tier_6',
        'tier_5',
        'tier_4',
        'tier_3',
        'tier_rates',
        'created_at',
        'updated_at'
    )
