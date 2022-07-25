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

#tarea que llama a tareas funciones , busca bloques
@app.task
def chain_find_blocks(channel_name, pool_id, pool_algorithm, miner,amount, limit):
    res = (iniciar_orden.s(str(channel_name), limit,pool_id,pool_algorithm, amount) | loop_find_n_blocks.s(str(channel_name),miner) | detener_orden.s(str(channel_name))  )()

    #res =(test_task.s() | test_task_2.s() | test_task_3.s())()
    return res
#

@shared_task
def iniciar_orden(channel_name, limit, pool, algoritmo, amount):
    print('Tarea iniciar_orden iniciada... ')
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj:': 'Tarea iniciar_orden iniciada...'
                                            
                                            }
                                      })
    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    
    private_api = nicehash.private_api(host, 
        organization_id, 
        key, 
        secret, 
        True)
    
    optimal_price=public_api.get_order_optimal_price('EU',algoritmo)
    optimal_price=optimal_price['price']
    optimal_price=float(optimal_price) + (float(optimal_price)*.1)
    #optimal_price="{:.4f}".format(optimal_price)
    optimal_price=float(optimal_price)
    optimal_price=round(optimal_price,4)
    
    print('algoritmo:')
    print(algoritmo)
    print('PRECIO OPTIMO: ')
    print(optimal_price)
    print('LIMITE:')
    print(limit)
    print('AMOUNT:')
    print(amount)
    print('POOL:')
    print(pool)
    print('algoritmos..')
    #print(algorithms)
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
        return order_id

@shared_task
def loop_find_n_blocks(order_id,channel_name,miner):
    print('Tarea find n blocks iniciada... ')
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj:':'Tarea find n blocks iniciada...',
                                                'order_id':order_id
                                            }
                                      })


    headers = {"User-Agent":"PostmanRuntime/7.29.0", "Accept":"*/*"}

    print('miner:')
    print(miner)
    n=2
    found=0

    bloques=[]

    #consultar bloques
    r = requests.get('https://etherscan.io/blocks', headers=headers)
    doc=html.fromstring(r.text)
    equis=doc.cssselect('tbody tr')

    for row in equis:
        #print('found')
        found_miner=row[5].text_content()
        print(found_miner.lower())
        if(found_miner.lower()==miner.lower().strip()):
            id_block=row[0][0].text_content()
            print(id_block)
            if str(id_block) not in bloques:
                bloques.append(str(id_block))
    
    print(bloques)
    #end consultar bloques

    #minutos=3
    #time.sleep(minutos*60)
    minutos_loop=3
    segundos_ciclo=30
    ciclos=(minutos_loop*60)/segundos_ciclo
    print(str(minutos_loop)+'minutos...')
    for i in range(int(ciclos)):
        print('ciclo:')
        print(i)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'ciclo:':i,
                                                'order_id':order_id
                                            }
                                      })
        r = requests.get('https://etherscan.io/blocks', headers=headers)

        doc=html.fromstring(r.text)
        equis=doc.cssselect('tbody tr')
        
        for row in equis:
            
            found_miner=row[5].text_content()
            print(found_miner)
            if(found_miner.lower()==miner.lower().strip()):
                id_block=row[0][0].text_content()
                print(id_block)
                if str(id_block) not in bloques:
                    bloques.append(str(id_block))
                    found+=1
        print(bloques)
        print('encontrados:')
        print(found)
        time.sleep(segundos_ciclo)

    minutos_loop=2
    segundos_ciclo=30
    ciclos=(minutos_loop*60)/segundos_ciclo
    print(str(minutos_loop)+'minutos...')
    for i in range(int(ciclos)):
        print('ciclo:')
        print(i)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'ciclo:':i,
                                                'order_id':order_id
                                            }
                                      })
        r = requests.get('https://etherscan.io/blocks', headers=headers)

        doc=html.fromstring(r.text)
        equis=doc.cssselect('tbody tr')
        
        for row in equis:
            
            found_miner=row[5].text_content()
            print(found_miner)
            if(found_miner.lower()==miner.lower().strip()):
                id_block=row[0][0].text_content()
                print(id_block)
                if str(id_block) not in bloques:
                    bloques.append(str(id_block))
                    found+=1
        print(bloques)
        print('encontrados:')
        print(found)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'encontrados:':found ,
                                                'order_id':order_id                                           
                                            }
                                      })
        if(found>=n):
            return order_id

        time.sleep(segundos_ciclo)

    return order_id


@shared_task
def detener_orden(order_id,channel_name):
    print('Tarea detener orden iniciada... ')
    print('order id: ')
    print(order_id)
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
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
                                                'log_time':str(datetime.now()),
                                                'status':'off',
                                                'msj':'Orden detenida',
                                                'order_id':order_id,
                                                'result':delete_hp_order,
                                            }
                                      })
    return delete_hp_order



@app.task
def chain_find_blocks_limit(channel_name, pool_id, pool_algorithm, miner,amount, limit):
    res = (iniciar_orden.s(str(channel_name), limit,pool_id,pool_algorithm, amount) | loop_find_n_blocks_limit.s(str(channel_name),miner, limit, pool_algorithm) | detener_orden.s(str(channel_name))  )()
    #res =(test_task.s() | test_task_2.s() | test_task_3.s())()
    return res
#


#tarea encontrar bloques w limit (?)
@shared_task
def loop_find_n_blocks_limit(order_id,channel_name,miner,limit, algoritmo):
    print('Tarea find n blocks iniciada... ')
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj:':'Tarea find n blocks w limit iniciada...',
                                                'order_id':order_id
                                            }
                                      })

    headers = {"User-Agent":"PostmanRuntime/7.29.0", "Accept":"*/*"}

    print('miner:')
    print(miner)
    n=2
    found=0
    bloques=[]

    #consultar bloques
    r = requests.get('https://etherscan.io/blocks', headers=headers)
    doc=html.fromstring(r.text)
    equis=doc.cssselect('tbody tr')

    for row in equis:
        #print('found')
        found_miner=row[5].text_content()
        print(found_miner.lower())
        if(found_miner.lower()==miner.lower().strip()):
            id_block=row[0][0].text_content()
            print(id_block)
            if str(id_block) not in bloques:
                bloques.append(str(id_block))
        print(bloques)

    #end consultar bloques


    #minutos=3
    #time.sleep(minutos*60)
    minutos_loop=3
    segundos_ciclo=30
    ciclos=(minutos_loop*60)/segundos_ciclo
    print(str(minutos_loop)+'minutos...')
    for i in range(int(ciclos)):
        print('ciclo:')
        print(i)
        r = requests.get('https://etherscan.io/blocks', headers=headers)
        doc=html.fromstring(r.text)
        equis=doc.cssselect('tbody tr')
        for row in equis:
            #print('found')
            found_miner=row[5].text_content()
            print(found_miner.lower())
            if(found_miner.lower()==miner.lower().strip()):
                id_block=row[0][0].text_content()
                print(id_block)
                if str(id_block) not in bloques:
                    bloques.append(str(id_block))
                    found+=1
            print(bloques)
        time.sleep(segundos_ciclo)
        
    #loop
    minutos_loop=2
    segundos_ciclo=30
    ciclos=(minutos_loop*60)/segundos_ciclo
    print(str(minutos_loop)+'minutos...')
    for i in range(int(ciclos)):
        print('ciclo:')
        print(i)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'ciclo:':i,
                                                'order_id':order_id
                                            }
                                      })
        r = requests.get('https://etherscan.io/blocks', headers=headers)

        doc=html.fromstring(r.text)
        equis=doc.cssselect('tbody tr')
        #found=0
        for row in equis:
            #print('found')
            found_miner=row[5].text_content()
            print(found_miner.lower())
            if(found_miner.lower()==miner.lower().strip()):
                id_block=row[0][0].text_content()
                print(id_block)    
                if str(id_block) not in bloques:
                    bloques.append(str(id_block))
                    found+=1
            print(bloques)
        print('encontrados:')
        print(found)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'encontrados:':found ,
                                                'bloques':bloques,
                                                'order_id':order_id                                           
                                            }
                                      })
        
        time.sleep(segundos_ciclo)
    if(found==0):
        return order_id


    #reducir limite
    print('limite inicial:')
    print(limit)
    limit=float(limit)-(float(limit)*0.9)
    print('limite:')
    print(limit)

    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    private_api = nicehash.private_api(host, 
        organization_id, 
        key, 
        secret, 
        True)

    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                            "message": 
                                                {
                                                    'log_time':str(datetime.now()),
                                                    'status':'on',
                                                    'msj':'Update limit iniciado...',
                                                    'order_id':order_id
                                                }
                                        })
    update=private_api.set_limit_hashpower_order(order_id, limit, algoritmo, algorithms)
    print(update)
    minutos=1.5
    time.sleep(minutos*60)
    return order_id



#tarea ciclo actualiza limit
@shared_task
def loop_update_limit(channel_name, pool, algoritmo,limit_1,limit_2, amount, time_limit):
    print('Tarea loop_update_limit iniciada... ')
    print('channel name: ')
    print(channel_name)
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj':'Tarea loop_update_limit iniciada... '
                                                
                                            }
                                      })
    #NICEHASH

    public_api = nicehash.public_api('https://api2.nicehash.com', True)
    algorithms = public_api.get_algorithms()
    
    private_api = nicehash.private_api(host, 
        organization_id, 
        key, 
        secret, 
        True)

    print('time limit:')
    print(float(time_limit))
    limit=limit_1
    
    optimal_price=public_api.get_order_optimal_price('EU',algoritmo)
    optimal_price=optimal_price['price']
    print('PRECIO OPTIMO: ')
    print(optimal_price)

    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'algoritmo':algoritmo,
                                            'precio_optimo':optimal_price,
                                            'limite':limit_1,
                                            'limite_2':limit_2,
                                            'amount':amount,
                                            'pool_id':pool
                                     } })

    new_order = private_api.create_hashpower_order('EU', 'STANDARD', algoritmo, optimal_price, limit, amount, pool , algorithms)
    print(new_order)
    if ('errors' in new_order):
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'off',
                                            'ERROR':new_order['errors']
                                     } })
        raise Exception('ERROR al crear la orden: '+str(new_order['errors']))
        print('ERROR al crear orden')
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

    time.sleep(float(time_limit)*60)
    limit=limit_2
    update=private_api.set_limit_hashpower_order(order_id, limit, algoritmo, algorithms)
    print(update)
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'msj':'Limite actualizado',
                                            'limite':limit,
                                            'order_id':order_id
                                     } })
    time.sleep(float(time_limit)*60)

    for i in range(9):
        limit=limit_1
        update=private_api.set_limit_hashpower_order(order_id, limit, algoritmo, algorithms)
        print(update)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'msj':'Limite actualizado',
                                            'limite':limit,
                                            'order_id':order_id
                                     } })
        time.sleep(float(time_limit)*60)
        limit=limit_2
        update=private_api.set_limit_hashpower_order(order_id, limit, algoritmo, algorithms)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'on',
                                            'msj':'Limite actualizado',
                                            'limite':limit,
                                            'order_id':order_id
                                     } })
        print(update)
        time.sleep(float(time_limit)*60)

    delete_hp_order = private_api.cancel_hashpower_order(order_id)
    print('CANCELAR orden ')
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": {
                                            'log_time':str(datetime.now()),
                                            'status':'off',
                                            'msj':'Orden Cancelada',
                                            'order_id':order_id
                                     } })
    print(delete_hp_order)

    return 'ok'


@app.task
def chain_find_blocks_stop(channel_name, pool_id, pool_algorithm, miner,amount, limit):
    res = (iniciar_orden.s(str(channel_name), limit,pool_id,pool_algorithm, amount) | loop_find_n_blocks_stop.s(str(channel_name),miner) | detener_orden.s(str(channel_name))  )()
    #res =(test_task.s() | test_task_2.s() | test_task_3.s())()
    return res
#


@shared_task
def loop_find_n_blocks_stop(order_id,channel_name,miner):
    print('Tarea find n blocks iniciada... ')
    async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'msj:':'Tarea find n blocks iniciada...',
                                                'order_id':order_id
                                            }
                                      })


    headers = {"User-Agent":"PostmanRuntime/7.29.0", "Accept":"*/*"}

    print('miner:')
    print(miner)
    n=1
    found=0

    bloques=[]

    #consultar bloques
    r = requests.get('https://etherscan.io/blocks', headers=headers)
    doc=html.fromstring(r.text)
    equis=doc.cssselect('tbody tr')

    for row in equis:
        #print('found')
        found_miner=row[5].text_content()
        print(found_miner.lower())
        if(found_miner.lower()==miner.lower().strip()):
            id_block=row[0][0].text_content()
            print(id_block)
            if str(id_block) not in bloques:
                bloques.append(str(id_block))
        print(bloques)

    #end consultar bloques

    minutos_loop=4
    segundos_ciclo=30
    ciclos=(minutos_loop*60)/segundos_ciclo

    for i in range(int(ciclos)):
        print('ciclo:')
        print(i)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'ciclo:':i,
                                                'order_id':order_id
                                            }
                                      })
        r = requests.get('https://etherscan.io/blocks', headers=headers)

        doc=html.fromstring(r.text)
        equis=doc.cssselect('tbody tr')
        
        for row in equis:
            
            found_miner=row[5].text_content()
            print(found_miner)
            if(found_miner.lower()==miner.lower().strip()):
                id_block=row[0][0].text_content()
                print(id_block)
                if str(id_block) not in bloques:
                    bloques.append(str(id_block))
                    found+=1
            print(bloques)
        print('encontrados:')
        print(found)
        async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": 
                                            {
                                                'log_time':str(datetime.now()),
                                                'status':'on',
                                                'encontrados:':found ,
                                                'order_id':order_id                                           
                                            }
                                      })
        if(found>=n):
            return order_id

        time.sleep(segundos_ciclo)

    return order_id














## TEEEEEEEEEST

# @shared_task
# #@app.task(bind=True, base=AbortableTask)
# def start_tarea(channel_name,inicio=None, tiempo=None, limite=None):

#     def crear_orden(limite):
#         #ORDEN
#         #market type algorithm price limit amount pool_id algo_response
#         #new_order = private_api.create_hashpower_order('EU', 'STANDARD', 'X16R', 0.123, 0, 0.005, pools_on_fist_page['list'][0]['id'], algorithms)
#         #print(new_order)
#         #END ORDEN
#         print('crear orden...')
#         return 'order_id'


#     task_id=start_tarea.request.id
    
#     #NICEHASH

#     public_api = nicehash.public_api('https://api2.nicehash.com', True)
#     algorithms = public_api.get_algorithms()

#     private_api = nicehash.private_api(host, 
#     organization_id, 
#     key, 
#     secret, 
#     True)

#     # Get pools
#     #pools_on_fist_page = private_api.get_my_pools('', '')
#     #print(pools_on_fist_page)

#     private_api = nicehash.private_api(host, 
#         organization_id, 
#         key, 
#         secret, 
#         True)



#     server='https://api.flexpool.io/v2'
#     coin='ETH'


#     order_id=crear_orden(limite)

#     def blocks(page):
#         lista=[]
#         print('pagina'+str(page))
#         luckg=0
#         url=server+'/pool/blocks?coin='+coin+'&page='+str(page)
#         r = requests.get(url)
#         result=r.json()['result']['data']
#         #print(result)
#         #print(result[0])
#         last_bloq=result[0]['luck']
#         for bloque in result:
#             luck=bloque['luck']
#             lista.append(luck)
#             luck=float(luck)*100
#             luckg=luck+luckg
#             print(str(luck) + '%')
#         arr = numpy.array(lista)
#         lista=arr*100
#         return dict(bloques=lista.tolist(),prom=luckg/10, last=last_bloq*100)
            
#     lista_comp=[]

#     i=0

#     list_all_blocks=[]

#     total_blocks_n=0

#     ######
#     while True:

#         nuevos_bloques=0
#         i+=1
#         promedio_total=0
#         bloque = blocks(0)
#         print('prom bloque '+str(bloque['prom']))
#         promedio_pagina0=bloque['prom']
#         ultimo=bloque['last']
        
#         promedio_total+=bloque['prom']

#         if(i==1):
#             list_all_blocks=bloque['bloques']

#         if (i!=1):
#             for b in bloque['bloques']:
#                 if b not in lista_comp:
#                     list_all_blocks.append(b)
#                     nuevos_bloques+=1

#         total_blocks_n+=nuevos_bloques

#         lista_comp=bloque['bloques']    


#         bloque=blocks(1)
#         print('prom bloque '+str(bloque['prom']))
#         promedio_total+=bloque['prom']
#         if(i==1):
#             list_all_blocks+=bloque['bloques']
#         bloque=blocks(2)
#         print('prom bloque '+str(bloque['prom']))
#         promedio_total+=bloque['prom']
#         if(i==1):
#             list_all_blocks+=bloque['bloques']

#         print('\nPromedio:'+str(promedio_total/3))
#         print('\nCantidad Bloques nuevos encontrados: '+str(nuevos_bloques))
#         print('Total Bloques nuevos encontrados: '+str(total_blocks_n))
#         print('Ultimo:' + str(ultimo))

#         print('\nAll bloques '+str(list_all_blocks))
        
#         numero_bloques=len(list_all_blocks)
#         sumatoria_luck=sum(list_all_blocks)
#         promedio_luck=sumatoria_luck/numero_bloques
        
#         print('\nNumero bloques '+str(numero_bloques))
#         print('Suma luck bloques '+str(sumatoria_luck))
#         print('Promedio luck bloques '+str(promedio_luck)+'\n')



#         async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
#                                         "message": {'num_bloques':str(numero_bloques),
#                                         'sum_luck_bloques':str(sumatoria_luck),
#                                          'prom_luck_bloques':str(promedio_luck),
#                                          'encontrados':str(numero_bloques-30),
#                                          'task_id': task_id ,
#                                          'status':'on',
#                                          'order_id': order_id
#                                      } })
#         print('send mensaje')
        
#         if (float(promedio_luck) <100):
#             #start_tarea.AsyncResult(start_tarea.request.id).abort()
#             #start_tarea.abort()
#             print('cancelar orden...')
#             continue
#             #delete_hp_order = private_api.cancel_hashpower_order(order_id)

#             #time.sleep(1)
#             #continue
#             #async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
#             #                            "message": {'status':'off',
#             #                            'encontrados':str(numero_bloques-30),
#             #                         } })
#             #app.control.revoke(task_id, terminate=True)
            
                
#             #get_orders = private_api.get_my_active_orders('','',10)
#             #if(len(get_orders['list'])>0):
#                 #order_id=get_orders['list'][0]['id']
#                 #delete_hp_order = private_api.cancel_hashpower_order(order_id)
                
#             #    pass
            
#         #print(start_tarea.request.state)
#         #print(start_tarea.AsyncResult(start_tarea.request.id).state)
        
#         time.sleep(3)

#     pass

# @shared_task
# def modificar_orden(limite):
#     pass


# @shared_task
# def detener_tarea(channel_name, task_id):
#     print(task_id)
#     #app.control.revoke(task_id, terminate=True)
#     AsyncResult(task_id).abort()
#     async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
#                                         "message": {'status':'off'
#                                      } })

# @shared_task
# def start_find_miner(channel_name, miner):
#     task_id=start_find_miner.request.id
    
#     headers = {"User-Agent":"PostmanRuntime/7.29.0", "Accept":"*/*"}

#     while True:

#         r = requests.get('https://etherscan.io/blocks', headers=headers)

#         doc=html.fromstring(r.text)
#         equis=doc.cssselect('tbody tr')
#         found=0
#         for row in equis:

#             found_miner=row[5].text_content()
#             if(found_miner.lower()==miner.lower().strip()):
#                 found+=1
#         async_to_sync(channel_layer.group_send)("tarea", {"type": "tarea.message", 
#                                 "message": {
#                                 'miner':miner,
#                                  'encontrado':str(found),
#                                  'task_id': task_id ,
#                                  'status':'on'
#                              } })
#         print(found)
#         if(found>=2):
#             #detener_tarea
#             pass

#         time.sleep(2)
    
    




# @shared_task
# def call_f(channel_name,inicio=None, tiempo=None, limite=None):
#     while True:
#         print('request..')
#         sleep(1)
#         pass


# @shared_task
# def test_task():
#     print('hello')
#     return 'HELLO'

# @shared_task
# def test_task_2(mensaje):
#     print('hello')
#     raise Exception
#     return mensaje + ' HELLO 2'

# @shared_task
# def test_task_3(mensaje):
#     print('hello')
#     return mensaje + ' HELLO 3'