import os
import json
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.utils import timezone
from .models import RateCalculation
from .forms import RateCalculationForm
from .calculator_engine import compute_rate_card, MARGIN_TIERS


def make_tier_pairs(tier_list):
    """Pairs 10 tiers into 5 rows (left: 15,13,11,10,8; right: 7,6,5,4,3) for clean 4-column pricing table"""
    left = tier_list[:5]
    right = tier_list[5:]
    pairs = []
    for l, r in zip(left, right):
        pairs.append({
            'left': {'margin': l['margin'], 'rate': l.get('selling_price_sqft') or l.get('rate')},
            'right': {'margin': r['margin'], 'rate': r.get('selling_price_sqft') or r.get('rate')},
        })
    return pairs


@ensure_csrf_cookie
def dashboard_view(request):
    """
    Main open dashboard view:
    - Renders calculation form and live mobile rate card preview.
    - History table is moved to dedicated Saved Calculations page (/history/).
    - Basic purchase rate excludes GST; 18% GST is automatically applied.
    """
    preview_data = None
    form = RateCalculationForm()
    total_saved = RateCalculation.objects.count()

    # Pre-populate with default sample data or query parameter
    load_id = request.GET.get('load')
    if load_id:
        try:
            target_calc = RateCalculation.objects.get(pk=load_id)
            form = RateCalculationForm(instance=target_calc)
            tier_list = target_calc.get_tier_list()
            preview_data = {
                'id': target_calc.id,
                'date': target_calc.date.strftime('%Y-%m-%d'),
                'product': target_calc.product,
                'thickness': float(target_calc.thickness),
                'weight_10ft': target_calc.weight_10ft,
                'landing_rate': target_calc.landing_rate,
                'rate_incl_gst': target_calc.rate_incl_gst,
                'ton_rate': target_calc.ton_rate,
                'sheets_per_ton': target_calc.sheets_per_ton,
                'sqft_per_ton': target_calc.sqft_per_ton,
                'cost_per_sqft': target_calc.cost_per_sqft,
                'tier_rates': target_calc.tier_rates,
                'tier_list': tier_list,
                'tier_row1': tier_list[:5],
                'tier_row2': tier_list[5:],
                'tier_pairs': make_tier_pairs(tier_list),
                'is_saved': True,
            }
            messages.info(request, f"Loaded saved calculation for '{target_calc.product}' ({target_calc.thickness}mm).")
        except RateCalculation.DoesNotExist:
            pass

    if request.method == 'POST':
        action = request.POST.get('action', 'calculate')
        form = RateCalculationForm(request.POST)

        if form.is_valid():
            product = form.cleaned_data['product']
            thickness = form.cleaned_data['thickness']
            weight_10ft = form.cleaned_data['weight_10ft']
            landing_rate = form.cleaned_data['landing_rate']
            date_val = form.cleaned_data['date']

            try:
                calc_results = compute_rate_card(
                    landing_rate=landing_rate,
                    weight_10ft=weight_10ft
                )

                if action == 'save':
                    instance = form.save()
                    messages.success(request, f"Rate card for '{instance.product}' saved successfully!")
                    return redirect(f"/?load={instance.id}")
                else:
                    tier_list = calc_results['tier_rates_list']
                    preview_data = {
                        'id': None,
                        'date': date_val.strftime('%Y-%m-%d'),
                        'product': product,
                        'thickness': float(thickness),
                        'weight_10ft': float(weight_10ft),
                        'landing_rate': float(landing_rate),
                        'rate_incl_gst': calc_results['rate_incl_gst'],
                        'ton_rate': calc_results['ton_rate'],
                        'sheets_per_ton': calc_results['sheets_per_ton'],
                        'sqft_per_ton': calc_results['sqft_per_ton'],
                        'cost_per_sqft': calc_results['cost_per_sqft'],
                        'tier_rates': calc_results['tier_rates'],
                        'tier_list': tier_list,
                        'tier_row1': tier_list[:5],
                        'tier_row2': tier_list[5:],
                        'tier_pairs': make_tier_pairs(tier_list),
                        'is_saved': False,
                    }
                    messages.info(request, "Calculation updated successfully.")
            except Exception as e:
                messages.error(request, f"Calculation error: {str(e)}")

    # If no preview data yet, generate default demo preview (e.g. Jindal 0.35mm, 8.4kg, 75/kg basic)
    if not preview_data:
        default_results = compute_rate_card(landing_rate=75.0, weight_10ft=8.4)
        def_tier_list = default_results['tier_rates_list']
        preview_data = {
            'id': None,
            'date': timezone.now().strftime('%Y-%m-%d'),
            'product': 'JINDAL',
            'thickness': 0.35,
            'weight_10ft': 8.4,
            'landing_rate': 75.0,
            'rate_incl_gst': default_results['rate_incl_gst'],
            'ton_rate': default_results['ton_rate'],
            'sheets_per_ton': default_results['sheets_per_ton'],
            'sqft_per_ton': default_results['sqft_per_ton'],
            'cost_per_sqft': default_results['cost_per_sqft'],
            'tier_rates': default_results['tier_rates'],
            'tier_list': def_tier_list,
            'tier_row1': def_tier_list[:5],
            'tier_row2': def_tier_list[5:],
            'tier_pairs': make_tier_pairs(def_tier_list),
            'is_saved': False,
        }
        form.initial.update({
            'product': 'JINDAL',
            'thickness': 0.35,
            'weight_10ft': 8.4,
            'landing_rate': 75.0,
        })

    context = {
        'form': form,
        'preview': preview_data,
        'total_saved': total_saved,
        'margin_tiers': MARGIN_TIERS,
    }
    return render(request, 'calculator/dashboard.html', context)


def history_view(request):
    """
    Dedicated page for viewing, searching, and managing all saved calculations.
    """
    search_query = request.GET.get('search', '').strip()
    history_qs = RateCalculation.objects.all().order_by('-date', '-created_at')

    if search_query:
        history_qs = history_qs.filter(product__icontains=search_query)

    context = {
        'history': history_qs,
        'search_query': search_query,
        'total_saved': RateCalculation.objects.count(),
        'filtered_count': history_qs.count(),
    }
    return render(request, 'calculator/history.html', context)


@require_http_methods(["POST"])
def calculate_api(request):
    """
    JSON API for real-time calculations.
    Basic rate excludes GST; 18% GST is added automatically.
    """
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        landing_rate = float(data.get('landing_rate', 0))
        weight_10ft = float(data.get('weight_10ft', 0))

        if weight_10ft <= 0:
            return JsonResponse({'error': 'Sheet weight must be greater than zero.'}, status=400)
        if landing_rate <= 0:
            return JsonResponse({'error': 'Basic rate must be greater than zero.'}, status=400)

        calc_results = compute_rate_card(
            landing_rate=landing_rate,
            weight_10ft=weight_10ft
        )
        return JsonResponse({'status': 'success', 'data': calc_results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
def save_calculation_api(request):
    """
    JSON API to persist calculation to database.
    """
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        form = RateCalculationForm(data)
        if form.is_valid():
            calc = form.save()
            return JsonResponse({
                'status': 'success',
                'id': calc.id,
                'message': f"Calculation for {calc.product} ({calc.thickness}mm) saved successfully!",
                'data': {
                    'id': calc.id,
                    'date': calc.date.strftime('%Y-%m-%d'),
                    'product': calc.product,
                    'thickness': float(calc.thickness),
                    'weight_10ft': calc.weight_10ft,
                    'landing_rate': calc.landing_rate,
                    'rate_incl_gst': calc.rate_incl_gst,
                    'ton_rate': calc.ton_rate,
                    'sheets_per_ton': calc.sheets_per_ton,
                    'sqft_per_ton': calc.sqft_per_ton,
                    'cost_per_sqft': calc.cost_per_sqft,
                    'tier_rates': calc.tier_rates,
                    'tier_list': calc.get_tier_list(),
                }
            })
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_calculation_api(request, pk):
    """
    Fetch a single calculation details for 'Load into Card' feature.
    """
    calc = get_object_or_404(RateCalculation, pk=pk)
    return JsonResponse({
        'status': 'success',
        'data': {
            'id': calc.id,
            'date': calc.date.strftime('%Y-%m-%d'),
            'product': calc.product,
            'thickness': float(calc.thickness),
            'weight_10ft': calc.weight_10ft,
            'landing_rate': calc.landing_rate,
            'rate_incl_gst': calc.rate_incl_gst,
            'ton_rate': calc.ton_rate,
            'sheets_per_ton': calc.sheets_per_ton,
            'sqft_per_ton': calc.sqft_per_ton,
            'cost_per_sqft': calc.cost_per_sqft,
            'tier_rates': calc.tier_rates,
            'tier_list': calc.get_tier_list(),
        }
    })


@require_http_methods(["POST", "DELETE"])
def delete_calculation_view(request, pk):
    """
    Delete a saved calculation from database.
    """
    calc = get_object_or_404(RateCalculation, pk=pk)
    product_name = calc.product
    thickness = calc.thickness
    calc.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'status': 'success',
            'message': f"Deleted {product_name} ({thickness}mm) successfully."
        })

    messages.success(request, f"Deleted calculation record for {product_name} ({thickness}mm).")
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('history_view')


def manifest_view(request):
    """
    Serve Web App Manifest JSON with correct MIME type.
    """
    manifest_path = os.path.join(settings.BASE_DIR, 'calculator', 'static', 'calculator', 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = "{}"
    return HttpResponse(content, content_type='application/manifest+json')


def service_worker_view(request):
    """
    Serve Service Worker JS with Service-Worker-Allowed header covering scope '/'.
    Ensures browsers do not cache sw.js so service worker updates deploy instantly.
    """
    sw_path = os.path.join(settings.BASE_DIR, 'calculator', 'static', 'calculator', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = ""
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
