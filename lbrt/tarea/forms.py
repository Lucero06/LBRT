from django import forms
from decouple import config
from . import nicehash


class Order_api(forms.Form):
    pool_id = forms.CharField(required=False)
    algorithm = forms.CharField(required=True)
    algorithms = forms.JSONField(required=True)
    amount = forms.CharField(required=False)
    limit = forms.CharField(required=False)
    order_id = forms.CharField(required=False)
    price = forms.CharField(required=False)


def get_pool_tuples(pools, lista=[]):
    for alg in pools:
        name = alg['name']+' - ' + \
            alg['stratumHostname']+' - '+alg['algorithm']
        value = alg['id']+"///"+alg['algorithm'] + '///'+alg['stratumHostname']
        pool_tuple = tuple([value, name])
        lista .append(pool_tuple)
    return lista


def select_choices():
    host = config('HOST_NC')
    organization_id = config('ORG_ID_NC')
    key = config('KEY_NC')
    secret = config('SECRET_NC')
    private_api = nicehash.private_api(
        host, organization_id, key, secret, True)
    pools_on_first_page = ''

    try:
        # pass
        pools_on_first_page = private_api.get_my_pools('', '')
    except Exception as inst:
        print('exception?')
        print(type(inst))    # the exception instance
        print(inst.args)     # arguments stored in .args
        print(inst)

    # Datos pools
    lista = []
    lista = get_pool_tuples(pools_on_first_page['list'], lista)
    total_pages = int(pools_on_first_page['pagination']['totalPageCount'])
    if (total_pages > 1):
        for i in range(total_pages-1):
            pools_on_page = private_api.get_my_pools(i+1, '')
            lista = get_pool_tuples(pools_on_page, lista)
    return lista


class create_order(forms.Form):
    pool = forms.ChoiceField(choices=select_choices(), required=True)
    amount = forms.FloatField(required=True)
    limit = forms.FloatField(required=True)
