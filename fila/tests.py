from django.test import TestCase
import fila.helpers as h
from .models import *
from django.forms.models import model_to_dict
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

    def send_and_consume(self, message, data=None):
        self.wsclient.send_and_consume('websocket.receive',
            text={
                "message": message,
                "data": data
            },
            path='/posto/')


    def ocupar_posto(self, posto):
        self.send_and_consume('OCUPAR_POSTO', {'posto': posto.pk})

    def chamar_seguinte(self):
        self.send_and_consume('CHAMR_SEGUINTE')

    def cancelar_chamado(self):
        self.send_and_consume('CANCELAR_CHAMADO')

    def finalizar_atencao(self):
        self.send_and_consume('FINALIZAR_ATENCAO')

    def desocupar_posto(self):
        self.send_and_consume('DESOCUPAR_POSTO')

    def atender(self):
        self.send_and_consume('ATENDER')

    def indicar_ausencia(self):
        self.send_and_consume('INDICAR_AUSENCIA')


class WSCliente(WSUsuario):

    def __init__(self, usuario, path='/fila/'):
        super(WSCliente, self).__init__(usuario, path)

    def entrar_na_fila(self, fila):
        self.wsclient.send_and_consume('websocket.receive',
            text={
                'message': 'ENTRAR_NA_FILA',
                'data': {
                    'fila': fila.pk
                },
            },
            path='/fila/')
        return Turno.objects.get(cliente=self.user,
            fila=fila,
            estado__in=[Turno.CLIENTE_CHAMADO, Turno.NA_FILA])

    def sair_da_fila(self, turno):
        self.wsclient.send_and_consume('websocket.receive',
            text={
                "message": "SAIR_DA_FILA",
                "data": {
                    'turno': turno.pk
                },
            },
            path='/fila/')


class EstadosPostoTestCase(ChannelTestCase):

    def test_inativo(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

    def test_em_pausa_apos_ocupado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')

        wsf1 = WSFuncionario(funcionario1)
        wsf1.ocupar_posto(posto1)

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

    def test_inativo_apos_desocupar(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')

        wsf1 = WSFuncionario(funcionario1)
        wsf1.ocupar_posto(posto1)

        wsf1.desocupar_posto()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

    def test_esperando_cliente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')

        wsf1 = WSFuncionario(funcionario1)
        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)
        self.assertIsNone(wsf1.receive())

    def test_em_pausa_apos_cancelar_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')

        wsf1 = WSFuncionario(funcionario1)
        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        wsf1.cancelar_chamado()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

    def test_cliente_chamado_apos_espera_cliente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.CLIENTE_CHAMADO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)
        self.assertEqual(wsf1.receive()['message'], 'CLIENTE_CHAMADO')


    def test_cliente_chamado_imediatamente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.CLIENTE_CHAMADO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)
        self.assertEqual(wsf1.receive()['message'], 'CLIENTE_CHAMADO')

    def test_atendendo(self):
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(wsf1.receive()['message'], 'CLIENTE_CHAMADO')

        wsf1.atender()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ATENDENDO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)

    def test_em_pausa_apos_cliente_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(wsf1.receive()['message'], 'CLIENTE_CHAMADO')

        wsf1.indicar_ausencia()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)
        self.assertEqual(posto1.turno_em_atencao, None)

    def test_em_pausa_apos_atendendo(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(wsf1.receive()['message'], 'CLIENTE_CHAMADO')

        wsf1.atender()

        wsf1.finalizar_atencao()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)
        self.assertEqual(posto1.turno_em_atencao, None)


class EstadosTurnoTestCase(ChannelTestCase):

    def test_na_fila(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NA_FILA)

    def test_cancelado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        wsc1 = WSCliente(cliente1)

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsc1.sair_da_fila(turno1)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.CANCELADO)
 
    def test_cliente_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.CLIENTE_CHAMADO)
 
    def test_no_atendimento(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.atender()

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NO_ATENDIMENTO)

    def test_atendido(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.atender()
        wsf1.finalizar_atencao()

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.ATENDIDO)

    def test_ausente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFuncionario(funcionario1)
        wsc1 = WSCliente(cliente1)

        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()

        turno1 = wsc1.entrar_na_fila(posto1.fila)

        wsf1.indicar_ausencia()

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.AUSENTE)

class Otra:

    def test_estados_atendido(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        cliente1 = h.get_or_create_cliente('c1')

        wsc1 = WSCliente(cliente1)
        self.assertEqual(
            wsc1.receive(),
            {"message": "QR_CODE", "data": {"qrcode": "c1"}}
            )

        turno1 = wsc1.entrar_na_fila(posto1.fila)
        self.assertEqual(
            wsc1.receive(),
            {"message": "ENTROU_NA_FILA", "turno": model_to_dict(turno1)}
            )

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
        wsc1.receive()

        turno1 = wsc1.entrar_na_fila(posto1.fila)
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NA_FILA)
        wsc1.receive()

        wsc1.sair_da_fila(turno1)
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.CANCELADO)

        turno1.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))
        turno1.fila.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))

    def test_estados_ausente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        cliente1 = h.get_or_create_cliente('c1')

        wsc1 = WSCliente(cliente1)
        self.assertEqual(
            wsc1.receive(),
            {"message": "QR_CODE", "data": {"qrcode": "c1"}}
            )

        turno1 = wsc1.entrar_na_fila(posto1.fila)
        self.assertEqual(
            wsc1.receive(),
            {"message": "ENTROU_NA_FILA", "turno": model_to_dict(turno1)}
            )

        funcionario1 = h.get_or_create_funcionario('f1')
        wsf1 = WSFuncionario(funcionario1)
        wsf1.ocupar_posto(posto1)

        wsf1.chamar_seguinte()
        self.assertEqual(wsc1.receive()['message'], 'IR_NO_POSTO')

        wsf1.indicar_ausencia()
        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.AUSENTE)
        turno1.get_grupo().send({'text':'ok'})
        self.assertIsNone(wsc1.receive(json=False))

        wsf1.desocupar_posto()

 
