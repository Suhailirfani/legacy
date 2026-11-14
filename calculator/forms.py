from django import forms
from django.utils import timezone
from .models import RateCalculation


class RateCalculationForm(forms.ModelForm):
    class Meta:
        model = RateCalculation
        fields = [
            'date',
            'product',
            'thickness',
            'weight_10ft',
            'landing_rate',
        ]
        widgets = {
            'date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                    'id': 'input-date',
                }
            ),
            'product': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. JINDAL, Sakthi, Duramet',
                    'id': 'input-product',
                    'list': 'product-presets',
                    'autocomplete': 'off',
                }
            ),
            'thickness': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. 0.35, 2.30',
                    'step': '0.01',
                    'min': '0.01',
                    'id': 'input-thickness',
                }
            ),
            'weight_10ft': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. 8.4',
                    'step': '0.01',
                    'min': '0.01',
                    'id': 'input-weight',
                }
            ),
            'landing_rate': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. 75.00',
                    'step': '0.01',
                    'min': '0.01',
                    'id': 'input-landing-rate',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()
