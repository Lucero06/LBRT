import time

from . import nicehash
import requests
import numpy

from asgiref.sync import async_to_sync
from celery import shared_task, group
from channels.layers import get_channel_layer
from django.core.cache import cache
#from celery.task.control import revoke
from lbrt.celery import app


from lxml import html
from cssselect import GenericTranslator, SelectorError
from lxml import etree
from io import StringIO, BytesIO

from celery.contrib.abortable import AbortableTask

from decouple import config

from datetime import datetime

channel_layer = get_channel_layer()


host=config('HOST_NC')
organization_id=config('ORG_ID_NC')
key=config('KEY_NC')
secret=config('SECRET_NC')
################# CRIPTO PROJECT

#PERIODIC

#pulsos
@shared_task
def loop_pulsos(channel_name, 
                num_pulsos, 
                limit, 
                limit_2, 
                pool, 
                algoritmo, 
                amount):
    print('numero de pulsos:')
    print(num_pulsos)

    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    
    private_api = nicehash.private_api(host, 
        organization_id, 
        key, 
        secret, 
        True)

    for i in range(int(num_pulsos)):
        algorithms = public_api.get_algorithms()

        optimal_price=public_api.get_order_optimal_price('EU',algoritmo)
        optimal_price=optimal_price['price']
        optimal_price=float(optimal_price) + (float(optimal_price)*.1)
        optimal_price=float(optimal_price)
        optimal_price=round(optimal_price,4)

        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'algoritmo':algoritmo,
                                            'precio_optimo':optimal_price,
                                            'limite':limit,
                                            'amount':amount,
                                            'pool_id':pool
                                     } })

        print('ciclo (pulso)')
        print(i)

        new_order = private_api.create_hashpower_order('EU', 'STANDARD', algoritmo, optimal_price, limit, amount, pool , algorithms)
        print(new_order)
        if ('errors' in new_order):

            async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                            "message": {
                                                'log_time':str(datetime.now()),
                                                'status':'off',
                                                'ERROR':new_order['errors']
                                        } })
            raise Exception('ERROR al crear la orden '+str(new_order['errors']))
            return 'error'
        else:
            order_id=new_order['id']
            async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                            "message": {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj':'Orden creada...',
                                                'order_id':order_id
                                        } })
            print('SUCCESS orden creada')

        minutos=5
        time.sleep(minutos*60)

        delete_hp_order = private_api.cancel_hashpower_order(order_id)
        print('Orden detenida: ')
        print(delete_hp_order)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                            "message": 
                                                {
                                                    'log_time':str(datetime.now()),
                                                    'status':'off',
                                                    'msj':'Orden detenida',
                                                    'order_id':order_id,
                                                    'result':delete_hp_order,
                                                }
                                        })
                
        minutos=55
        time.sleep(minutos*60)
