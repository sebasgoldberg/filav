from channels import Channel, Group
from channels.sessions import channel_session
from channels.auth import channel_session_user, channel_session_user_from_http
from .models import *

@channel_session_user_from_http
def ws_posto_connect(message):
    message.reply_channel.send({"accept": True})

@channel_session_user
def ws_posto_ocupar(message):
    f = Funcionario.get_from_user(message.user)
    p = Posto.objects.get(pk=message.content['posto'])
    f.ocupar_posto(p)
    p.get_grupo().add(message.reply_channel)

@channel_session_user
def ws_posto_chamar(message):
    f = Funcionario.get_from_user(message.user)
    f.chamar_seguinte()

@channel_session_user
def ws_posto_pausar(message):
    f = Funcionario.get_from_user(message.user)
    f.pausar_atencao()

@channel_session_user
def ws_posto_finalizar(message):
    f = Funcionario.get_from_user(message.user)
    f.finalizar_atencao()

@channel_session_user
def ws_posto_ausencia(message):
    f = Funcionario.get_from_user(message.user)
    f.indicar_ausencia()

@channel_session_user
def ws_posto_atender(message):
    f = Funcionario.get_from_user(message.user)
    f.atender()

@channel_session_user
def ws_posto_desocupar(message):
    f = Funcionario.get_from_user(message.user)
    f.desocupar_posto()


from channels.generic.websockets import JsonWebsocketConsumer
from django.forms.models import model_to_dict
import json

class FilaConsumer(JsonWebsocketConsumer):

    # Set to True if you want it, else leave it out
    strict_ordering = False
    http_user = True

    def connection_groups(self, **kwargs):
        return []

    def connect(self, message, **kwargs):
        if self.message.user.is_authenticated:
            c = Cliente.get_from_user(self.message.user)
            grupo_cliente = c.get_grupo()
            grupo_cliente.add(self.message.reply_channel)
            super(FilaConsumer, self).connect(message, **kwargs)
            grupo_cliente.send({
                'text': json.dumps({
                    "message": "QR_CODE",
                    "data":{
                        "qrcode": self.message.user.username,
                    }
                })
            })

    def entrar_na_fila(self, content):
        c = Cliente.get_from_user(self.message.user)
        f = Fila.objects.get(pk=content['fila'])
        t = c.entrar_na_fila(f)
        t.get_grupo().add(self.message.reply_channel)
        f.get_grupo().add(self.message.reply_channel)
        c.get_grupo().send({
            'text': json.dumps({
                'message': 'ENTROU_NA_FILA',
                'turno': model_to_dict(t),
            })})

    def sair_da_fila(self, content):
        c = Cliente.get_from_user(self.message.user)
        t = Turno.objects.get(pk=content['turno'], cliente=c)
        t.cancelar()

    def enviar_filas(self, data):
        cliente = Cliente.objects.get(username=data['qrcode'])
        local = Local.objects.get(pk=data['local'])
        filas = [ model_to_dict(f) for f in local.filas.all() ]
        cliente.get_grupo().send({
            'text': json.dumps({
                'message': 'FILAS_DISPONIBLES',
                'data':{
                    'filas': filas,
                },
            })})

    def receive(self, content, **kwargs):
        if self.message.user.is_authenticated:
            if content['message'] == 'ENTRAR_NA_FILA':
                self.entrar_na_fila(content['data'])
            elif content['message'] == 'ENVIAR_FILAS':
                self.enviar_filas(content['data'])
            elif content['message'] == 'SAIR_DA_FILA':
                self.sair_da_fila(content['data'])

    def disconnect(self, message, **kwargs):
        if self.message.user.is_authenticated:
            PersistedGroup.remove_channel_from_groups(self.message.reply_channel)

