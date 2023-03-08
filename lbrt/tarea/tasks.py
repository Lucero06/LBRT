import time

from . import nicehash
from .models import Order, Task
from django_celery_results.models import TaskResult
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from lbrt.celery import app
from .forms import Order_api
from celery import states, Task as celerytask

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


class BaseClassTask(celerytask):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # exc (Exception) - The exception raised by the task.
        # args (Tuple) - Original arguments for the task that failed.
        # kwargs (Dict) - Original keyword arguments for the task that failed.
        send_msg_updt_orders()
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                          "message": {
                                                              'tarea': str(task_id),
                                                              'log_time': str(datetime.now()),
                                                              'status': 'off',
                                                              'ERROR': str(exc)
                                                          }})


@app.task
def stop_task(task_id):
    stop_order.update_state(task_id, state=states.SUCCESS)
    app.control.revoke(task_id, terminate=True)
    send_msg_updt_orders()


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
                send_msg_updt_orders()
            else:
                raise Exception('ERROR al detener la orden ' +
                                str(delete_hp_order['errors']))
    else:
        o = Order.objects.get(order_id=order_id)
        o.status = 'Detenida'
        o.save()
        send_msg_updt_orders()
    return delete_hp_order


def send_msg_updt_orders():
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                      "message": {
                                                          'update_orders': True
                                                      }})


def create_order(private_api,
                 order_data: Order_api):
    new_order = private_api.create_hashpower_order(
        'EU', 'STANDARD',
        order_data['algorithm'],
        order_data['price'],
        order_data['limit'],
        order_data['amount'],
        order_data['pool_id'],
        order_data['algorithms'])
    # print(new_order)
    return new_order


def update_limit(private_api,
                 limit,
                 order_id,
                 algorithm,
                 algorithms
                 ):
    update = private_api.set_limit_hashpower_order(
        order_id, limit, algorithm, algorithms)
    if ('errors' in update):
        for error in update['errors']:
            if (error['code'] == 5058):
                o = Order.objects.get(order_id=order_id)
                o.status = 'Detenida'
                o.save()
                # task_id = o.tasks.first().task_id
                # stop_task(task_id)
        raise Exception('ERROR al actualizar limit ' +
                        str(update['errors']))
    return update


def update_price(
        order_data: Order_api,
        private_api=None,
):
    update = private_api.set_price_hashpower_order(
        order_data['order_id'],
        order_data['price'],
        order_data['algorithm'],
        order_data['algorithms']
    )
    if ('errors' in update):
        pass
    return update


def time_func(time_var):
    print(time_var)
    time.sleep(int(time_var))


def get_optimal_price(algorithm, public_api=None):
    if (public_api == None):
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


@app.task(bind=True, base=BaseClassTask)
def iniciar_orden(self, channel_name, pool_id, pool_algorithm, time_up, time_down, amount, limit_up, limit_down, porcentaje_decimal, name_tarea):
    global contador
    # send_msg_updt_orders()
    # return True
    optimal_price_save = []
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

    optimal_price = get_optimal_price(pool_algorithm, public_api)
    optimal_price = adjust_optimal_price(optimal_price, porcentaje_decimal)

    # print(self.request)
    task_id = self.request.id
    order_data = Order_api({
        'pool_id': pool,
        'algorithm': algorithm,
        'algorithms': algorithms,
        'limit': limit_up,
        'amount': amount,
        'price': optimal_price
    })
    order_data.is_valid()
    new_order = create_order(private_api, order_data.cleaned_data)
    # new_order = {'id': 1}
    if ('errors' in new_order):
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
        optimal_price_save.append(optimal_price)
        o = Order(order_id=order_id, status='Iniciada')
        o.save()
        taskO = TaskResult.objects.get(task_id=task_id)
        t = Task(order=o, task_id=task_id, task_object=taskO)
        t.save()
        send_msg_updt_orders()

    while True:
        # tiempo arriba
        print(optimal_price_save)
        print(contador)
        if (contador > 1):  # primera vez no pasa
            optimal_price = get_optimal_price(pool_algorithm, public_api)
            if (optimal_price < optimal_price_save[0]*2.5):

                optimal_price = adjust_optimal_price(
                    optimal_price, porcentaje_decimal)

                optimal_price_save.append(optimal_price)

                update_limit(private_api, limit_up,
                             order_id, algorithm, algorithms)
            else:
                async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                                  "message": {
                                                                      'tarea': str(name_tarea),
                                                                      'log_time': str(datetime.now()),
                                                                      'status': 'on',
                                                                      'msj': 'NO se hace update del limit porque el optimal price actual es mayor al anterior...',
                                                                      'order_id': order_id
                                                                  }})
        time_func(time_up)
        update_limit(private_api, limit_down,
                     order_id, algorithm, algorithms)
        time_func(time_down)
        contador += 1


def adjust_optimalprice_downstep(optimal_price, algorithm, public_api):
    buy_info = public_api.buy_info()
    response = buy_info['miningAlgorithms']
    # print(algorithm)
    for alg in response:
        # print(alg['name'])
        # print(alg['down_step'])
        if alg['name'].upper() == algorithm.upper():
            down_step = alg['down_step']
    optimal_price += down_step
    return optimal_price


@app.task(bind=True, base=BaseClassTask)
def order_price(self, channel_name, pool_id, pool_algorithm, amount, limit, porcentaje_decimal, name_tarea):
    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    pool = pool_id
    algorithm = pool_algorithm

    private_api = nicehash.private_api(host,
                                       organization_id,
                                       key,
                                       secret,
                                       True)
    optimal_price = get_optimal_price(pool_algorithm, public_api)
    optimal_price = adjust_optimal_price(optimal_price, porcentaje_decimal)

    task_id = self.request.id
    order_data = Order_api({
        'pool_id': pool,
        'algorithm': algorithm,
        'algorithms': algorithms,
        'limit': limit,
        'amount': amount,
        'price': optimal_price
    })

    order_data.is_valid()
    print(order_data.cleaned_data)
    new_order = create_order(private_api, order_data.cleaned_data)
    # new_order = {'id': 1}
    if ('errors' in new_order):
        raise Exception('ERROR al crear la orden '+str(new_order['errors']))
    else:
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
        send_msg_updt_orders()

    while True:
        time.sleep(600)
        optimal_price = adjust_optimalprice_downstep(
            optimal_price, algorithm, public_api)
        print('price')
        print(optimal_price)
        update = private_api.set_price_hashpower_order(
            order_id, optimal_price, algorithm, algorithms)
        print(update)
