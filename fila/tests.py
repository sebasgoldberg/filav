from django.test import TestCase
import fila.helpers as h
from .models import *
from django.forms.models import model_to_dict
from channels import Group
from channels.test import ChannelTestCase, WSClient
from django.utils import timezone as TZ
from datetime import timedelta as TD

class WSUsuario:

    def __init__(self, usuario, path='/'):
        self.user = usuario
        self.wsclient = WSClient()
        self.wsclient.force_login(usuario)
        self.wsclient.send_and_consume('websocket.connect', path=path)
        self.path = path
    
    def receive(self, *args, **kwargs):
        return self.wsclient.receive(*args, **kwargs)

    def send_and_consume(self, message, data=None):
        self.wsclient.send_and_consume('websocket.receive',
            text={
                "message": message,
                "data": data
            },
            path=self.path)


class WSPosto(WSUsuario):

    def __init__(self, usuario, path='/posto/'):
        super(WSPosto, self).__init__(usuario, path)

    def get_postos_inativos(self, local):
        self.send_and_consume('GET_POSTOS_INATIVOS', {'local': local.pk})

    def ocupar_posto(self, posto):
        self.send_and_consume('OCUPAR_POSTO', {'posto': posto.pk})

    def chamar_seguinte(self):
        self.send_and_consume('CHAMAR_SEGUINTE')

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


class WSFila(WSUsuario):

    def __init__(self, usuario, path='/fila/'):
        super(WSFila, self).__init__(usuario, path)

    def entrar_na_fila(self, fila, qrcode=None):
        _qrcode = qrcode
        if _qrcode is None:
            qrcode, _ = QRCode.objects.get_or_create(user=self.user)
            qrcode.local = fila.local
            qrcode.save()
            _qrcode = qrcode.qrcode

        self.send_and_consume('ENTRAR_NA_FILA', {'fila': fila.pk, 'qrcode': _qrcode})
        return Turno.objects.get(cliente=self.user,
            fila=fila,
            estado__in=[Turno.CLIENTE_CHAMADO, Turno.NA_FILA])

    def sair_da_fila(self, turno):
        self.send_and_consume('SAIR_DA_FILA', {'turno': turno.pk})


class WSScanner(WSUsuario):

    def __init__(self, usuario, path='/scanner/'):
        super(WSScanner, self).__init__(usuario, path)

    def scan(self, qrcode, local):
        self.send_and_consume('SCAN', {'qrcode': qrcode, 'local': local.pk})


class SequenciaIngressoTestCase(ChannelTestCase):

    def test_get_codigo_qr(self):

        cliente1 = h.get_or_create_cliente('c1')
        wsf1 = WSFila(cliente1)

        qrcode = QRCode.objects.get(user=cliente1)
        self.assertEqual(
            wsf1.receive(),
            {"message": "QR_CODE", "data": {"qrcode": qrcode.qrcode}}
            )

    def test_scann_e_enviar_filas(self):

        cliente1 = h.get_or_create_cliente('c1')
        scann1 = h.get_or_create_funcionario_scanner('s1')
        h.get_or_create_posto(['l1', 'f1', 'p1'])
        local1 = h.get_or_create_posto(['l1', 'f2', 'p2']).fila.local

        wsf1 = WSFila(cliente1)
        qrcode = wsf1.receive()['data']['qrcode']

        wss1 = WSScanner(scann1)
        wss1.scan(qrcode, local1)

        QRCode.objects.get(user=cliente1, qrcode=qrcode, local=local1)

        filas = [model_to_dict(f) for f in local1.filas.all()]
        self.assertEqual(
            wsf1.receive(),
            {   
                "message": "FILAS_DISPONIBLES",
                "data": {"qrcode": qrcode, 'filas': filas}
            })

    def test_entrar_na_fila(self):

        cliente1 = h.get_or_create_cliente('c1')
        scann1 = h.get_or_create_funcionario_scanner('s1')
        h.get_or_create_posto(['l1', 'f1', 'p1'])
        local1 = h.get_or_create_posto(['l1', 'f2', 'p2']).fila.local

        wsf1 = WSFila(cliente1)
        qrcode = wsf1.receive()['data']['qrcode']

        wss1 = WSScanner(scann1)
        wss1.scan(qrcode, local1)


        filas = [model_to_dict(f) for f in local1.filas.all()]
        data = wsf1.receive()['data']
        
        fila = Fila.objects.get(pk=data['filas'][0]['id'])
        turno = wsf1.entrar_na_fila(fila,data['qrcode'])

        self.assertEqual(
            wsf1.receive(),
            {   
                "message": "TURNO_ATIVO",
                "data": {'turno': turno.to_dict()}
            })


class EstadosPostoTestCase(ChannelTestCase):

    def test_inativo(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])

        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

    def test_em_pausa_apos_ocupado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)
        wsp1.ocupar_posto(posto1)

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

    def test_inativo_apos_desocupar(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)
        wsp1.ocupar_posto(posto1)

        wsp1.desocupar_posto()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.INATIVO)
        self.assertIsNone(posto1.funcionario)

    def test_esperando_cliente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)
        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

    def test_em_pausa_apos_cancelar_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)
        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        wsp1.cancelar_chamado()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)

    def test_cliente_chamado_apos_espera_cliente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ESPERANDO_CLIENTE)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.CLIENTE_CHAMADO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)


    def test_cliente_chamado_imediatamente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.CLIENTE_CHAMADO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)

    def test_atendendo(self):
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        posto1.refresh_from_db()

        wsp1.atender()
        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.ATENDENDO)
        self.assertEqual(posto1.turno_em_atencao.pk, turno1.pk)

    def test_em_pausa_apos_cliente_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        posto1.refresh_from_db()

        wsp1.indicar_ausencia()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)
        self.assertEqual(posto1.turno_em_atencao, None)

    def test_em_pausa_apos_atendendo(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        posto1.refresh_from_db()

        wsp1.atender()

        wsp1.finalizar_atencao()

        posto1.refresh_from_db()
        self.assertEqual(posto1.estado, Posto.EM_PAUSA)
        self.assertEqual(posto1.funcionario.pk, funcionario1.pk)
        self.assertEqual(posto1.turno_em_atencao, None)


class EstadosTurnoTestCase(ChannelTestCase):

    def test_na_fila(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFila(cliente1)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NA_FILA)

    def test_cancelado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        wsf1 = WSFila(cliente1)

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsf1.sair_da_fila(turno1)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.CANCELADO)
 
    def test_cliente_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.CLIENTE_CHAMADO)
 
    def test_no_atendimento(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.atender()

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.NO_ATENDIMENTO)

    def test_atendido(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.atender()
        wsp1.finalizar_atencao()

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.ATENDIDO)

    def test_ausente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        cliente1 = h.get_or_create_cliente('c1')

        wsp1 = WSPosto(funcionario1)
        wsf1 = WSFila(cliente1)

        wsp1.ocupar_posto(posto1)

        wsp1.chamar_seguinte()

        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1.indicar_ausencia()

        turno1.refresh_from_db()
        self.assertEqual(turno1.estado, Turno.AUSENTE)

class MensagensFuncionarioTestCase(ChannelTestCase):

    def test_connect_sem_posto_ativo(self):
       
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "LOCAIS_DISPONIVEIS",
                "data": {'locais': [model_to_dict(l) for l in Local.objects.all()]}
            })

        self.assertIsNone(wsp1.receive())

    def test_connect_com_posto_ativo(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        funcionario1.ocupar_posto(posto1)
        posto1.refresh_from_db()

        wsp1 = WSPosto(funcionario1)

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_get_postos_inativos(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.get_postos_inativos(Local.objects.first())

        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTOS_INATIVOS",
                "data": {'postos': [model_to_dict(p) for p in posto1.local.postos.filter(
                    estado=Posto.INATIVO)]}
            })

        self.assertIsNone(wsp1.receive())

    def test_ocupar_posto(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_chamar_seguinte(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.chamar_seguinte()

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_cancelar_chamado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.chamar_seguinte()

        wsp1.receive()

        wsp1.cancelar_chamado()

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_cliente_em_caminho(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.chamar_seguinte()

        wsp1.receive()

        self.assertIsNone(wsp1.receive())

        cliente1 = h.get_or_create_cliente('c1')
        wsf1 = WSFila(cliente1)
        turno1 = wsf1.entrar_na_fila(posto1.fila)

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_atender(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        cliente1 = h.get_or_create_cliente('c1')
        wsf1 = WSFila(cliente1)
        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.chamar_seguinte()

        wsp1.receive()
        wsp1.receive()

        wsp1.atender()

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_indicar_ausencia(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        cliente1 = h.get_or_create_cliente('c1')
        wsf1 = WSFila(cliente1)
        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.chamar_seguinte()

        wsp1.receive()
        wsp1.receive()

        wsp1.indicar_ausencia()

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_finalizar_atencao(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        cliente1 = h.get_or_create_cliente('c1')
        wsf1 = WSFila(cliente1)
        turno1 = wsf1.entrar_na_fila(posto1.fila)

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.chamar_seguinte()

        wsp1.receive()
        wsp1.receive()

        wsp1.atender()

        wsp1.receive()

        wsp1.finalizar_atencao()

        posto1.refresh_from_db()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "POSTO",
                "data": {'posto': posto1.to_dict()}
            })

        self.assertIsNone(wsp1.receive())

    def test_desocupar(self):
       
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        funcionario1 = h.get_or_create_funcionario_posto('f1')

        wsp1 = WSPosto(funcionario1)

        wsp1.receive()

        wsp1.ocupar_posto(posto1)

        wsp1.receive()

        wsp1.desocupar_posto()

        wsp1.receive()
        self.assertEqual(
            wsp1.receive(),
            {   
                "message": "LOCAIS_DISPONIVEIS",
                "data": {'locais': [model_to_dict(l) for l in Local.objects.all()]}
            })

        self.assertIsNone(wsp1.receive())

class TempoEsperaTestCase(TestCase):

    def test_inicio_espera_date_null(self):
        
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        t1 = cliente1.entrar_na_fila(posto1.fila.id, h.get_or_create_qrcode(cliente1, posto1.fila).qrcode)

        self.assertIsNone(t1.inicio_espera_date)

    def test_inicio_espera_date_registrado(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        t1 = cliente1.entrar_na_fila(posto1.fila.id, h.get_or_create_qrcode(cliente1, posto1.fila).qrcode)

        t1.estado = Turno.CLIENTE_CHAMADO
        ini_save = TZ.now()
        t1.save()
        end_save = TZ.now()

        self.assertGreaterEqual(t1.inicio_espera_date, ini_save)
        self.assertLessEqual(t1.inicio_espera_date, end_save)

    def test_fim_espera_date_null(self):
        
        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        t1 = cliente1.entrar_na_fila(posto1.fila.id, h.get_or_create_qrcode(cliente1, posto1.fila).qrcode)

        self.assertIsNone(t1.fim_espera_date)

    def test_turno_finalizado_registrado_atendido(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        t1 = cliente1.entrar_na_fila(posto1.fila.id, h.get_or_create_qrcode(cliente1, posto1.fila).qrcode)

        t1.estado = Turno.ATENDIDO
        ini_save = TZ.now()
        t1.save()
        end_save = TZ.now()

        self.assertGreaterEqual(t1.fim_espera_date, ini_save)
        self.assertLessEqual(t1.fim_espera_date, end_save)

    def test_turno_finalizado_registrado_ausente(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        t1 = cliente1.entrar_na_fila(posto1.fila.id, h.get_or_create_qrcode(cliente1, posto1.fila).qrcode)

        t1.estado = Turno.AUSENTE
        ini_save = TZ.now()
        t1.save()
        end_save = TZ.now()

        self.assertGreaterEqual(t1.fim_espera_date, ini_save)
        self.assertLessEqual(t1.fim_espera_date, end_save)

    def test_media_tempo_espera_um_turno(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        t1 = cliente1.entrar_na_fila(posto1.fila.id, test_mode=True)

        t1.estado = Turno.ATENDIDO
        t1.inicio_espera_date = TZ.now()
        t1.fim_espera_date = t1.inicio_espera_date + TD(seconds=355)

        t1.save()

        t1.fila.refresh_from_db()

        t1.fila.calcular_media_espera(dt_from=t1.inicio_espera_date, dt_to=t1.fim_espera_date)

        self.assertEqual(t1.fila.media_espera, 355)

    def test_media_tempo_espera_multiples_turnos(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        # (inicio atendimento, tempo atendimento): Simulamos 2 postos de atendimento
        esperas = [(0,355), (15,299), (356,344), (314,600), (700,245), (914,33)]
        media = sum(map(lambda x: x[1],esperas))/len(esperas)
        inicio_atendimento = TZ.now()
        fim_atendimento = inicio_atendimento + TD(seconds=950)

        for espera in esperas:
            t1 = cliente1.entrar_na_fila(posto1.fila.id, test_mode=True)
            t1.estado = Turno.ATENDIDO
            t1.inicio_espera_date = inicio_atendimento + TD(seconds=espera[0])
            t1.fim_espera_date = t1.inicio_espera_date + TD(seconds=espera[1])
            t1.save()

        t1.fila.refresh_from_db()

        t1.fila.calcular_media_espera(dt_from=inicio_atendimento, dt_to=fim_atendimento)

        t1.refresh_from_db()

        self.assertEqual(t1.fila.media_espera, media)

    def test_media_tempo_espera_por_fila(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        posto2 = h.get_or_create_posto(['l1', 'f2', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        # (inicio atendimento, tempo atendimento): Simulamos 2 postos de atendimento
        esperas = [(0,355), (15,299), (356,344), (314,600), (700,245), (914,33)]
        media = sum(map(lambda x: x[1],esperas))/len(esperas)
        inicio_atendimento = TZ.now()
        fim_atendimento = inicio_atendimento + TD(seconds=950)

        t1 = cliente1.entrar_na_fila(posto2.fila.id, test_mode=True)
        t1.estado = Turno.ATENDIDO
        t1.inicio_espera_date = inicio_atendimento + TD(seconds=10)
        t1.fim_espera_date = t1.inicio_espera_date + TD(seconds=600)
        t1.save()

        for espera in esperas:
            t1 = cliente1.entrar_na_fila(posto1.fila.id, test_mode=True)
            t1.estado = Turno.ATENDIDO
            t1.inicio_espera_date = inicio_atendimento + TD(seconds=espera[0])
            t1.fim_espera_date = t1.inicio_espera_date + TD(seconds=espera[1])
            t1.save()

        t1.fila.refresh_from_db()

        t1.fila.calcular_media_espera(dt_from=inicio_atendimento, dt_to=fim_atendimento)

        t1.refresh_from_db()

        self.assertEqual(t1.fila.media_espera, media)


    def test_media_tempo_espera_qtd_minima_turnos(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        # (inicio atendimento, tempo atendimento): Simulamos 2 postos de atendimento
        esperas = [(0,355), (15,299), (356,344), (314,600), (700,245), (914,33)]
        media = sum(map(lambda x: x[1],esperas))/len(esperas)
        inicio_atendimento = TZ.now()
        fim_atendimento = inicio_atendimento + TD(seconds=950)

        for espera in esperas:
            t1 = cliente1.entrar_na_fila(posto1.fila.id, test_mode=True)
            t1.estado = Turno.ATENDIDO
            t1.inicio_espera_date = inicio_atendimento + TD(seconds=espera[0])
            t1.fim_espera_date = t1.inicio_espera_date + TD(seconds=espera[1])
            t1.save()

        t1.fila.refresh_from_db()

        t1.fila.media_espera = 500
        t1.fila.save()

        t1.fila.refresh_from_db()

        with self.assertRaises(SemQtdMinTurnosParaCalcularMediaEspera):
            t1.fila.calcular_media_espera(dt_from=inicio_atendimento, dt_to=fim_atendimento, qtd_min_turnos=7)

        t1.refresh_from_db()

        self.assertEqual(t1.fila.media_espera, 500)

class EstimaEsperaTestCase(TestCase):

    def test_estima_espera_um_cliente_sem_posto_ativo(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        posto1.fila.media_espera = 11
        posto1.fila.save()

        t1 = cliente1.entrar_na_fila(posto1.fila.pk, test_mode=True)

        self.assertEqual(t1.estimar_tempo_espera(),11)

    def test_estima_espera_um_cliente_um_posto(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')

        funcionario1 = h.get_or_create_funcionario_posto('f1')
        funcionario1.ocupar_posto(posto1)

        posto1.fila.media_espera = 11
        posto1.fila.save()

        t1 = cliente1.entrar_na_fila(posto1.fila.pk, test_mode=True)

        self.assertEqual(t1.estimar_tempo_espera(),11)

    def test_estima_espera_multiples_clientes_um_posto(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        cliente1 = h.get_or_create_cliente('c1')
        cliente2 = h.get_or_create_cliente('c2')
        cliente3 = h.get_or_create_cliente('c3')

        funcionario1 = h.get_or_create_funcionario_posto('f1')
        funcionario1.ocupar_posto(posto1)

        posto1.fila.media_espera = 11
        posto1.fila.save()

        t1 = cliente1.entrar_na_fila(posto1.fila.pk, test_mode=True)
        t2 = cliente2.entrar_na_fila(posto1.fila.pk, test_mode=True)
        t3 = cliente3.entrar_na_fila(posto1.fila.pk, test_mode=True)

        self.assertEqual(t1.estimar_tempo_espera(),11)
        self.assertEqual(t2.estimar_tempo_espera(),22)
        self.assertEqual(t3.estimar_tempo_espera(),33)


    def test_estima_espera_multiples_clientes_multiples_postos(self):

        posto1 = h.get_or_create_posto(['l1', 'f1', 'p1'])
        posto2 = h.get_or_create_posto(['l1', 'f1', 'p2'])
        posto3 = h.get_or_create_posto(['l1', 'f1', 'p3'])
        cliente1 = h.get_or_create_cliente('c1')
        cliente2 = h.get_or_create_cliente('c2')
        cliente3 = h.get_or_create_cliente('c3')
        funcionario1 = h.get_or_create_funcionario_posto('f1')
        funcionario2 = h.get_or_create_funcionario_posto('f2')

        funcionario1.ocupar_posto(posto1)
        funcionario2.ocupar_posto(posto2)

        posto1.fila.media_espera = 11
        posto1.fila.save()

        t1 = cliente1.entrar_na_fila(posto1.fila.pk, test_mode=True)
        t2 = cliente2.entrar_na_fila(posto1.fila.pk, test_mode=True)
        t3 = cliente3.entrar_na_fila(posto1.fila.pk, test_mode=True)

        self.assertEqual(t1.estimar_tempo_espera(),5.5)
        self.assertEqual(t2.estimar_tempo_espera(),11)
        self.assertEqual(t3.estimar_tempo_espera(),16.5)

