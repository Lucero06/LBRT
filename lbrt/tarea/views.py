from django.contrib import messages
from django.views.generic import TemplateView
from django.shortcuts import render

from datetime import datetime, timedelta, date
from dateutil import tz
from django.utils import timezone
import pytz

from . import nicehash
import requests
import json
from django.db.models import Q
from django.db.models import Count
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from django_celery_results.models import TaskResult

from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required

from decouple import config

from tarea.models import Order, Task

from django import template

register = template.Library()


# @register.filter()
# def update_variable(value):
#     data = value
#     return data


# register.filter('update_variable', update_variable)


def query_order():
    tasks_not_ended = Count('id', filter=~Q(
        tasks__task_object__status__in=['SUCCESS', 'REVOKED', 'FAILURE']))
    orders = Order.objects.prefetch_related(
        'tasks').annotate(num_tasks=tasks_not_ended).order_by('-id').all().filter(~Q(status='Detenida')
                                                                                  | Q(inicio=date.today())
                                                                                  | Q(num_tasks__gt=0)
                                                                                  )
    return orders


def update_items(request):
    orders = query_order()
    return render(request, 'tarea/order_table.html', {'orders': orders})


@register.filter()
def query_filter(value, attr):
    return value.filter(**eval(attr))


@method_decorator(staff_member_required, name='dispatch')
class TareaView(TemplateView):

    template_name = 'tarea/tarea.html'

    # print(pools_on_first_page)
    # pools=json.loads(pools_on_first_page)

    def get_context_data(self, **kwargs):
        # Datos que se van a mostrar en la interfaz (template, vista) en la pantalla que ve el usuario

        # Dato hora actual
        context = super().get_context_data(**kwargs)
        hora = datetime.now().hour
        context['hora'] = str(hora).zfill(2)
        minuto = datetime.now()
        # minuto=minuto+timedelta(minutes=1)
        context['minuto'] = str(minuto.minute).zfill(2)
        context['segundo'] = datetime.now().second

        # Conexión y datos NiceHash
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
        # print(pools_on_first_page)
        context['pools'] = pools_on_first_page['list']
        # print(len(pools_on_first_page['list']))
        total_pages = int(pools_on_first_page['pagination']['totalPageCount'])
        if (total_pages > 1):
            for i in range(total_pages-1):
                print(i+1)
                pools_on_page = private_api.get_my_pools(i+1, '')
                # print(pools_on_page)
                print(len(pools_on_page['list']))
                context['pools'] += pools_on_page['list']
        # print(context['pools'])

        # Datos Cuenta Balance
        balance = private_api.get_accounts_for_currency('BTC')
        balance_currency = ''
        balance_available = 0
        balance_total = 0
        balance_debt = 0
        balance_pending = 0
        balance_btcRate = 0
        if (not 'errors' in balance):
            balance_total = balance['totalBalance']
            balance_available = balance['available']
            balance_debt = balance['debt']
            balance_pending = balance['pending']
            balance_btcRate = balance['btcRate']
            balance_currency = balance['currency']
        context['balance_total'] = balance_total
        context['balance_available'] = balance_available
        context['balance_debt'] = balance_debt
        context['balance_pending'] = balance_pending
        context['balance_btcRate'] = balance_btcRate
        context['balance_currency'] = balance_currency

        # balance_currency=balance['']
        # print(balance)
        # Valores por defecto para la interfaz (y que se pueden cambiar en interfaz)
        # limit=0.1
        # amount=0.001
        # context['limit']=limit
        # context['amount']=amount

        # Obtener Datos Tareas gaurdadas
        schedules = IntervalSchedule.objects.all()
        periodic_tasks = PeriodicTask.objects.order_by('-id').all()
        periodic_tasks = list(periodic_tasks)
        # print(periodic_tasks)
        # class_date = timezone.localtime(self.class_date)
        timezone = pytz.timezone("America/Mexico_City")
        for task in periodic_tasks:
            # print(task.last_run_at.astimezone(timezone).strftime('%H:%M'))
            if (task.last_run_at is not None):
                task.last_run_at = task.last_run_at.astimezone(
                    timezone).strftime('%H:%M')
        # print(schedules.count())
        # print(PeriodicTask.objects.values())
        print(TaskResult.objects.values())
        # tasks_results=TaskResult.objects.all().values('task_id').distinct()

        # Obtener Datos Resultados de Tareas
        tasks_not_ended = Count('id', filter=~Q(
            tasks__task_object__status__in=['SUCCESS', 'REVOKED', 'FAILURE']))
        orders = Order.objects.prefetch_related(
            'tasks').annotate(num_tasks=tasks_not_ended).order_by('-id').all().filter(~Q(status='Detenida')
                                                                                      | Q(inicio=date.today())
                                                                                      | Q(num_tasks__gt=0)
                                                                                      )
        # print('orders:')
        # print(orders[0].tasks.__dict__)
        tasks = Task.objects.select_related("order").order_by('-id').all()[:5]
        tasks_results = TaskResult.objects.order_by('-id').all()[:5]

        # Datos Tareas y Resultados de tareas
        context['schedules'] = list(schedules)
        context['periodic_tasks'] = periodic_tasks
        context['orders'] = list(orders)
        context['tasks'] = list(tasks)
        context['tasks_results'] = list(tasks_results)
        context['wsport'] = config('WS_PORT')
        # print(context)
        return context
