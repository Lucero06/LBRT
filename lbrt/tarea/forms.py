from django import forms


class Order_api(forms.Form):
    pool_id = forms.CharField(required=False)
    algorithm = forms.CharField(required=True)
    algorithms = forms.JSONField(required=True)
    amount = forms.CharField(required=False)
    limit = forms.CharField(required=False)
    order_id = forms.CharField(required=False)
    price = forms.CharField(required=False)
