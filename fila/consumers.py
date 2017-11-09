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
def ws_posto_desocupar(message):
    f = Funcionario.get_from_user(message.user)
    f.desocupar_posto()

@channel_session_user_from_http
def ws_fila_connect(message):
    message.reply_channel.send({"accept": True})

@channel_session_user
def ws_fila_entrar(message):
    c = Cliente.get_from_user(message.user)
    f = Fila.objects.get(pk=message.content['fila'])
    t = c.entrar_na_fila(f)
    t.get_grupo().add(message.reply_channel)
    f.get_grupo().add(message.reply_channel)

