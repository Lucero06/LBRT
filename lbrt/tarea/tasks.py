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

from web3 import Web3

from lxml import html
from cssselect import GenericTranslator, SelectorError
from lxml import etree

from io import StringIO, BytesIO

from celery.contrib.abortable import AbortableTask

from decouple import config

from datetime import datetime

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

channel_layer = get_channel_layer()

#nicehash
host=config('HOST_NC')
organization_id=config('ORG_ID_NC')
key=config('KEY_NC')
secret=config('SECRET_NC')
#end nicehash

# infura
infura_url = config('INFURA_URL')
web3 = Web3(Web3.HTTPProvider(infura_url))
#end infura

################# CRIPTO PROJECT
headers = {
        "User-Agent":"User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36", 
        "Accept":"*/*"
        }

#tarea que llama a tareas funciones , busca bloques
@app.task
def chain_order_up(channel_name, pool_id, pool_algorithm, time_up,amount, limit, porcentaje_decimal,name_tarea):
    res = (iniciar_orden.s(str(channel_name), limit,pool_id,pool_algorithm, amount, porcentaje_decimal,name_tarea) | time_up_task.s(str(channel_name),time_up,name_tarea) | detener_orden.s(str(channel_name),name_tarea))()
    return res
#

@shared_task
def iniciar_orden(channel_name, limit, pool, algoritmo, amount, porcentaje_decimal,name_tarea):
    print(name_tarea)
    print('Tarea iniciar_orden iniciada... ')
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj:': str(name_tarea)+': Tarea iniciar_orden iniciada...'
                                            
                                            }
                                      })
    #oruebas
    #return 'TEST ORDER ID'
    #end pruebas
    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    
    private_api = nicehash.private_api(host, 
        organization_id, 
        key, 
        secret, 
        True)
    
    optimal_price=public_api.get_order_optimal_price('EU',algoritmo)
    optimal_price=optimal_price['price']
    print('PRECIO OPTIMO: ')
    print(optimal_price)

    optimal_price=float(optimal_price) + (float(optimal_price)*float(porcentaje_decimal))
    optimal_price=float(optimal_price)
    optimal_price=round(optimal_price,4)
    print('PRECIO OPTIMO + porcentaje: ')
    print(optimal_price)

    print('algoritmo:')
    print(algoritmo)
    print('LIMITE:')
    print(limit)
    print('AMOUNT:')
    print(amount)
    print('POOL:')
    print(pool)
    #print('algoritmos..')
    #print(algorithms)
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'tarea':str(name_tarea),
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'algoritmo':algoritmo,
                                            'precio_optimo':optimal_price,
                                            'limite':limit,
                                            'amount':amount,
                                            'pool_id':pool
                                     } })
    

    new_order = private_api.create_hashpower_order('EU', 'STANDARD', algoritmo, optimal_price, limit, amount, pool , algorithms)
    print(new_order)
    if ('errors' in new_order):

        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'tarea':str(name_tarea),
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
                                            'tarea':str(name_tarea),
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'msj':'Orden creada...',
                                            'order_id':order_id
                                     } })
        print('SUCCESS orden creada')
        return order_id

@shared_task
def time_up_task(order_id,channel_name,time_up,name_tarea):
    try:
        print(name_tarea)
        print('Tarea time up iniciada... ')
        print('tiempo:')
        print(time_up)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                            "message": 
                                                {
                                                    'tarea':str(name_tarea),
                                                    'log_time':str(datetime.now()),
                                                    'status':'on',
                                                    'msj:':'Tarea time_up iniciada...',
                                                    'order_id':order_id,
                                                    'tiempo': str(time_up)
                                                }
                                        })
        time.sleep(int(time_up))

    except Exception as e:
        logger.error('ERROR capturado:')
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'tarea':str(name_tarea),
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj':'ERROR capturado',
                                                'order_id':order_id
                                            }
                                      })
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'tarea': str(name_tarea),
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj':str(e),
                                                'order_id':order_id
                                            }
                                      })
        logger.error(e)
        return order_id
    return order_id

@shared_task
def detener_orden(order_id,channel_name,name_tarea):
    print(name_tarea)
    print('Tarea detener orden iniciada... ')
    print('order id: ')
    print(order_id)
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'tarea':str(name_tarea),
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj':'Tarea detener orden iniciada... ',
                                                'order_id':order_id
                                            }
                                      })
    #nicehash
    
    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    
    private_api = nicehash.private_api(host, 
        organization_id, 
        key, 
        secret, 
        True)
    #end nicehash

    delete_hp_order = private_api.cancel_hashpower_order(order_id)
    print('Orden detenida: ')
    print(delete_hp_order)
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'tarea':str(name_tarea),   
                                                'log_time':str(datetime.now()),
                                                'status':'off',
                                                'msj':'Orden detenida',
                                                'order_id':order_id,
                                                'result':delete_hp_order,
                                            }
                                      })
    return delete_hp_order


