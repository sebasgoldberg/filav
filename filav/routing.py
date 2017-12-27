from channels.routing import route, include, route_class
from fila.consumers import *

posto_routing = [
    route_class(PostoConsumer, path=r"^/"),
]

fila_routing = [
    route_class(FilaConsumer, path=r"^/"),
]

channel_routing = [
    include(posto_routing, path=r'^/posto'),
    include(fila_routing, path=r'^/fila'),
]
