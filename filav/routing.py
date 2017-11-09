from channels.routing import route, include
from fila.consumers import *

posto_routing = [
    route("websocket.connect", ws_posto_connect, path=r'^/$'),
    route("websocket.receive", ws_posto_ocupar, path=r'^/ocupar/$'),
    route("websocket.receive", ws_posto_chamar, path=r'^/chamar/$'),
    route("websocket.receive", ws_posto_pausar, path=r'^/pausar/$'),
    route("websocket.receive", ws_posto_finalizar, path=r'^/finalizar/$'),
    route("websocket.receive", ws_posto_desocupar, path=r'^/desocupar/$'),
    #route("websocket.disconnect", ws_disconnect_posto),
]

fila_routing = [
    route("websocket.connect", ws_fila_connect, path=r'^/$'),
    route("websocket.receive", ws_fila_entrar, path=r'^/entrar/$'),
    route("websocket.receive", ws_fila_sair, path=r'^/sair/$'),
]

channel_routing = [
    include(posto_routing, path=r'^/posto'),
    include(fila_routing, path=r'^/fila'),
]
