from django.test import TestCase
import fila.helpers as h
from .models import *

class FilaTestCase(TestCase):
    
    def test_estados_posto(self):

        funcionario1 = h.get_or_create_funcionario('f1')
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

        funcionario1.ocupar_posto(posto1)

        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.EM_PAUSA)

        funcionario1.chamar_seguinte()

        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

        funcionario1.pausar_atencao()
        
        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.EM_PAUSA)

        funcionario1.chamar_seguinte()

        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

        cliente1 = h.get_or_create_cliente('c1')
        turno1 = cliente1.entrar_na_fila(posto1.fila)
        posto1.atender(turno1)

        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.ATENDENDO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)

        funcionario1.finalizar_atencao()

        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertIsNone(posto1.turno_em_atencao)

        funcionario1.desocupar_posto()

        posto1.refresh_from_db()

        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

from channels import Group
from channels.test import ChannelTestCase, WSClient

class WSUsuario:

    def __init__(self, usuario, path='/'):
        self.user = usuario
        self.wsclient = WSClient()
        self.wsclient.force_login(usuario)
        self.wsclient.send_and_consume('websocket.connect', path=path)
    
    def receive(self, *args, **kwargs):
        return self.wsclient.receive(*args, **kwargs)


class WSFuncionario(WSUsuario):

    def __init__(self, usuario, path='/posto/'):
        super(WSFuncionario, self).__init__(usuario, path)

    def ocupar_posto(self, posto):
        self.wsclient.send_and_consume('websocket.receive',
            {'posto': str(posto.pk)},
            path='/posto/ocupar/')

    def chamar_seguinte(self):
        self.wsclient.send_and_consume('websocket.receive',
            path='/posto/chamar/')

    def pausar_atencao(self):
        self.wsclient.send_and_consume('websocket.receive',
            path='/posto/pausar/')

    def finalizar_atencao(self):
        self.wsclient.send_and_consume('websocket.receive',
            path='/posto/finalizar/')

    def desocupar_posto(self):
        self.wsclient.send_and_consume('websocket.receive',
            path='/posto/desocupar/')

class WSCliente(WSUsuario):

    def __init__(self, usuario, path='/fila/'):
        super(WSCliente, self).__init__(usuario, path)

    def entrar_na_fila(self, fila):
        self.wsclient.send_and_consume('websocket.receive',
            {'fila': fila.pk},
            path='/fila/entrar/')
        return Turno.objects.get(cliente=self.user,
            fila=fila,
            estado__in=[Turno.NO_ATENDIMENTO, Turno.NA_FILA])

    def sair_da_fila(self, turno):
        self.wsclient.send_and_consume('websocket.receive',
            {'turno': turno.pk},
            path='/fila/sair/')


class PostoTestCase(ChannelTestCase):

    def test_estados(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

        funcionario1 = h.get_or_create_funcionario('f1')

        wsf1 = WSFuncionario(funcionario1)

        wsf1.ocupar_posto(posto1)

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

        wsf1.chamar_seguinte()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)
        self.assertIsNone(wsf1.receive())

        wsf1.pausar_atencao()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)

        wsf1.chamar_seguinte()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)
        self.assertIsNone(wsf1.receive())

        cliente1 = h.get_or_create_cliente('c1')
        wsc1 = WSCliente(cliente1)
        turno1 = wsc1.entrar_na_fila(posto1.fila)
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ATENDENDO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)
        self.assertEqual(wsf1.receive()['message'], 'ATENDER_TURNO')

        wsf1.finalizar_atencao()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertIsNone(posto1.turno_em_atencao)

        wsf1.desocupar_posto()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)


class TurnoTestCase(ChannelTestCase):

    def test_estados_atendido(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        cliente1 = h.get_or_create_cliente('c1')

        wsc1 = WSCliente(cliente1)
        turno1 = wsc1.entrar_na_fila(posto1.fila)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NA_FILA)
        turno1.get_grupo().send({'text':'ok'})
        self.assertEqual(wsc1.receive(json=False), 'ok')
        turno1.fila.get_grupo().send({'text':'ok'})
        self.assertEqual(wsc1.receive(json=False), 'ok')

        funcionario1 = h.get_or_create_funcionario('f1')
        wsf1 = WSFuncionario(funcionario1)
        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NO_ATENDIMENTO)
        self.assertEqual(wsc1.receive()['message'], 'IR_NO_POSTO')
        turno1.get_grupo().send({'text':'ok'})
        self.assertEqual(wsc1.receive(json=False), 'ok')
        turno1.fila.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))

        wsf1.finalizar_atencao()
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.ATENDIDO)
        turno1.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))

        wsf1.desocupar_posto()

    def test_estados_cancelado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        cliente1 = h.get_or_create_cliente('c1')

        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NA_FILA)

        wsc1.sair_da_fila(turno1)
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.CANCELADO)

        turno1.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))
        turno1.fila.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))

