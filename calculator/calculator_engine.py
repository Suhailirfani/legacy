"""
Core calculation engine for Roofing Margin & Rate Card Calculator.
"""

from decimal import Decimal

# Fixed Constants
GST_RATE = 0.18
NET_WEIGHT_KG = 1000.0  # 1 Metric Ton
SHEET_AREA_SQFT = 36.0  # 10 ft length × 3.6 ft standard width
MARGIN_TIERS = [15, 13, 11, 10, 8, 7, 6, 5, 4, 3]


def compute_rate_card(landing_rate: float, weight_10ft: float, is_gst_included: bool = False):
    """
    Computes step-by-step math for roofing sheet costing and selling price tiers.
    Basic purchase rate is strictly excluding GST; 18% GST is always added.

    Formulas:
    1. rate_incl_gst = landing_rate * 1.18 (landing_rate is basic rate excluding GST)
    2. ton_rate = rate_incl_gst * 1000
    3. sheets_per_ton = 1000 / weight_10ft
    4. sqft_per_ton = sheets_per_ton * 36.0
    5. cost_per_sqft = ton_rate / sqft_per_ton
    6. For each margin M in [15, 13, 11, 10, 8, 7, 6, 5, 4, 3]:
       selling_price_sqft = (ton_rate + (M * 1000)) / sqft_per_ton (Rounded to 2 decimal places)
    """
    landing_rate = float(landing_rate)
    weight_10ft = float(weight_10ft)
    if weight_10ft <= 0:
        raise ValueError("10ft sheet weight must be greater than zero.")

    # Basic rate excludes GST -> Add 18% GST
    rate_incl_gst = landing_rate * (1.0 + GST_RATE)

    ton_rate = rate_incl_gst * NET_WEIGHT_KG
    sheets_per_ton = NET_WEIGHT_KG / weight_10ft
    sqft_per_ton = sheets_per_ton * SHEET_AREA_SQFT
    cost_per_sqft = ton_rate / sqft_per_ton if sqft_per_ton > 0 else 0.0

    tier_rates_dict = {}
    tier_rates_list = []

    for margin in MARGIN_TIERS:
        selling_price_sqft = (ton_rate + (margin * NET_WEIGHT_KG)) / sqft_per_ton
        rounded_rate = round(selling_price_sqft, 2)
        tier_rates_dict[str(margin)] = rounded_rate
        tier_rates_list.append({
            'margin': margin,
            'selling_price_sqft': rounded_rate,
            'margin_ton': margin * NET_WEIGHT_KG,
        })

    return {
        'rate_incl_gst': round(rate_incl_gst, 2),
        'ton_rate': round(ton_rate, 2),
        'sheets_per_ton': round(sheets_per_ton, 2),
        'sqft_per_ton': round(sqft_per_ton, 2),
        'cost_per_sqft': round(cost_per_sqft, 2),
        'tier_rates': tier_rates_dict,
        'tier_rates_list': tier_rates_list,
    }
