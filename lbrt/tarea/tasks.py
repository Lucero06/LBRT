import time

from . import nicehash

from .models import Order, Task
from django_celery_results.models import TaskResult

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from lbrt.celery import app

from celery import states

from decouple import config

from datetime import datetime

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

channel_layer = get_channel_layer()

# nicehash
host = config('HOST_NC')
organization_id = config('ORG_ID_NC')
key = config('KEY_NC')
secret = config('SECRET_NC')


@app.task
def stop_task(task_id):
    stop_order.update_state(task_id, state=states.SUCCESS)
    app.control.revoke(task_id, terminate=True)


@app.task
def stop_order(order_id, private_api=None):
    print('Tarea detener orden iniciada... ')
    if (private_api is None):
        private_api = nicehash.private_api(host,
                                           organization_id,
                                           key,
                                           secret,
                                           True)
    print('order id: ')
    print(order_id)
    delete_hp_order = private_api.cancel_hashpower_order(order_id)

    if ('errors' in delete_hp_order):
        print(delete_hp_order['errors'][0])
        for error in delete_hp_order['errors']:
            if (error['code'] == 5058):
                o = Order.objects.get(order_id=order_id)
                o.status = 'Detenida'
                o.save()
            else:
                raise Exception('ERROR al detener la orden ' +
                                str(delete_hp_order['errors']))
    else:
        o = Order.objects.get(order_id=order_id)
        o.status = 'Detenida'
        o.save()
    return delete_hp_order


def create_order(private_api,
                 algorithm,
                 optimal_price,
                 limit_up,
                 amount,
                 pool,
                 algorithms):
    new_order = private_api.create_hashpower_order(
        'EU', 'STANDARD', algorithm, optimal_price, limit_up, amount, pool, algorithms)
    print(new_order)
    return new_order


def update_limit(private_api,
                 limit,
                 order_id,
                 algorithm,
                 algorithms
                 ):
    update = private_api.set_limit_hashpower_order(
        order_id, limit, algorithm, algorithms)
    return update


def time_func(time_var):
    print(time_var)
    time.sleep(int(time_var))


def get_optimal_price(algorithm):
    public_api = nicehash.public_api('https://api2.nicehash.com', True)

    optimal_price = public_api.get_order_optimal_price('EU', algorithm)
    optimal_price = optimal_price['price']
    print('PRECIO OPTIMO: ')
    print(optimal_price)
    optimal_price = float(optimal_price)
    optimal_price = round(optimal_price, 4)
    print(optimal_price)
    return optimal_price


def adjust_optimal_price(optimal_price, porcentaje_decimal):
    optimal_price = float(optimal_price) + \
        (float(optimal_price)*float(porcentaje_decimal))
    optimal_price = float(optimal_price)
    optimal_price = round(optimal_price, 4)
    print('PRECIO OPTIMO + porcentaje: ')
    print(optimal_price)

    return optimal_price


contador = 0


@app.task(bind=True)
def iniciar_orden(self, channel_name, pool_id, pool_algorithm, time_up, time_down, amount, limit_up, limit_down, porcentaje_decimal, name_tarea):
    global contador

    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    pool = pool_id
    algorithm = pool_algorithm

    private_api = nicehash.private_api(host,
                                       organization_id,
                                       key,
                                       secret,
                                       True)
    print('tiempo u'+str(time_up))
    print('tiempo d'+str(time_down))

    # return True

    contador += 1
    optimal_price = get_optimal_price(pool_algorithm)
    optimal_price = adjust_optimal_price(optimal_price, porcentaje_decimal)

    # print(self.request)
    task_id = self.request.id

    new_order = create_order(private_api, algorithm,
                             optimal_price, limit_up, amount, pool, algorithms)
    # new_order = {'id': 1}
    if ('errors' in new_order):
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                          "message": {
                                                              'tarea': str(name_tarea),
                                                              'log_time': str(datetime.now()),
                                                              'status': 'off',
                                                              'ERROR': new_order['errors']
                                                          }})
        raise Exception('ERROR al crear la orden '+str(new_order['errors']))
    else:
        contador += 1
        order_id = new_order['id']
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                          "message": {
                                                              'tarea': str(name_tarea),
                                                              'log_time': str(datetime.now()),
                                                              'status': 'on',
                                                              'msj': 'Orden creada...',
                                                              'order_id': order_id
                                                          }})
        print('SUCCESS orden creada')
        o = Order(order_id=order_id, status='Iniciada')
        o.save()
        taskO = TaskResult.objects.get(task_id=task_id)
        t = Task(order=o, task_id=task_id, task_object=taskO)
        t.save()

    while True:
        # tiempo arriba
        if (contador > 1):
            update_limit(private_api, limit_up,
                         order_id, algorithm, algorithms)
        time_func(time_up)
        update_limit(private_api, limit_down,
                     order_id, algorithm, algorithms)
        time_func(time_down)
