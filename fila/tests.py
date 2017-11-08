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
        self.wsclient = WSClient()
        self.wsclient.force_login(usuario)
        self.wsclient.send_and_consume('websocket.connect', path=path)
    
    def receive(self, *args, **kwargs):
        return self.wsclient.receive(*args, **kwargs)


class WSFuncionario(WSUsuario):

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

    def entrar_na_fila(self, fila):
        self.wsclient.send_and_consume('websocket.receive',
            {'fila': fila.pk},
            path='/fila/entrar/')


class PostoTestCase(ChannelTestCase):

    def test_estados(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

        funcionario1 = h.get_or_create_funcionario('f1')

        wsf1 = WSFuncionario(funcionario1, '/posto/')

        wsf1.ocupar_posto(posto1)

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

        # El funcionario entre no grupo do posto de forma de conseguir comunicar
        # quando teve alguma mudança de estado.
        posto1.get_grupo().send({'text': 'ok'}, immediately=True)
        self.assertEqual(wsf1.receive(json=False), 'ok')

        wsf1.chamar_seguinte()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

        wsf1.pausar_atencao()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)

        wsf1.chamar_seguinte()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

        cliente1 = h.get_or_create_cliente('c1')
        wsc1 = WSCliente(cliente1, '/fila/')
        wsc1.entrar_na_fila(posto1.fila)
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ATENDENDO)
        self.assertEqual(posto1.turno_em_atencao.pk,
            Turno.objects.get(cliente=cliente1, fila=posto1.fila,
                estado=Turno.NO_ATENDIMENTO).pk)

        wsf1.finalizar_atencao()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertIsNone(posto1.turno_em_atencao)

        wsf1.desocupar_posto()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

