from channels.routing import route, include, route_class
from fila.consumers import *

posto_routing = [
    route("websocket.connect", ws_posto_connect, path=r'^/$'),
    route("websocket.receive", ws_posto_ocupar, path=r'^/ocupar/$'),
    route("websocket.receive", ws_posto_chamar, path=r'^/chamar/$'),
    route("websocket.receive", ws_posto_pausar, path=r'^/pausar/$'),
    route("websocket.receive", ws_posto_finalizar, path=r'^/finalizar/$'),
    route("websocket.receive", ws_posto_desocupar, path=r'^/desocupar/$'),
    route("websocket.receive", ws_posto_ausencia, path=r'^/ausencia/$'),
    #route("websocket.disconnect", ws_disconnect_posto),
]

fila_routing = [
    route_class(FilaConsumer, path=r"^/"),
]

channel_routing = [
    include(posto_routing, path=r'^/posto'),
    include(fila_routing, path=r'^/fila'),
]
