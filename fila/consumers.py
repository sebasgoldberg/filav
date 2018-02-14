from channels import Channel, Group
from channels.sessions import channel_session
from channels.auth import channel_session_user, channel_session_user_from_http
from .models import *
from channels.generic.websockets import JsonWebsocketConsumer
from django.forms.models import model_to_dict
import json


class PostoConsumer(JsonWebsocketConsumer):

    # Set to True if you want it, else leave it out
    strict_ordering = False
    http_user = True

    def connection_groups(self, **kwargs):
        return []

    def connect(self, message, **kwargs):
        if self.message.user.is_authenticated:
            if self.message.user.has_perm('fila.atender_clientes'):
                super(PostoConsumer, self).connect(message, **kwargs)
                self.funcionario = Funcionario.get_from_user(self.message.user)
                self.funcionario.get_grupo().add(self.message.reply_channel)
                self.get_estado()

    def disconnect(self, message, **kwargs):
        if self.message.user.is_authenticated:
            PersistedGroup.remove_channel_from_groups(self.message.reply_channel)

    def ocupar_posto(self, content):
        p = Posto.objects.get(pk=content['posto'])
        self.funcionario.ocupar_posto(p)

    def chamar_seguinte(self, content):
        self.funcionario.chamar_seguinte()

    def cancelar_chamado(self, content):
        self.funcionario.cancelar_chamado()

    def finalizar_atencao(self, content):
        self.funcionario.finalizar_atencao()

    def indicar_ausencia(self, content):
        self.funcionario.indicar_ausencia()

    def atender(self, content):
        self.funcionario.atender()

    def desocupar_posto(self, content):
        self.funcionario.desocupar_posto()
        self.get_estado()

    def get_estado(self):
        try:
            self.funcionario.posto.notificar()
        except Posto.DoesNotExist:
            self.get_locais_disponiveis()

    def get_locais_disponiveis(self):
        locais = [ model_to_dict(l) for l in Local.objects.all() ]
        self.funcionario.get_grupo().send({
            'text': json.dumps({
                'message': 'LOCAIS_DISPONIVEIS',
                'data': { 'locais': locais, }
            })})
        
    def get_postos_inativos(self, data):
        local_id = data['local']
        local = Local.objects.get(pk=local_id)
        postos = [ model_to_dict(p) for p in local.postos.filter(
            estado=Posto.INATIVO) ]
        self.funcionario.get_grupo().send({
            'text': json.dumps({
                'message': 'POSTOS_INATIVOS',
                'data': { 'postos': postos, }
            })})

    def receive(self, content, **kwargs):
        if self.message.user.is_authenticated:
            if self.message.user.has_perm('fila.atender_clientes'):
                self.funcionario = Funcionario.get_from_user(self.message.user)
                if content['message'] == 'OCUPAR_POSTO':
                    self.ocupar_posto(content['data'])
                elif content['message'] == 'CHAMAR_SEGUINTE':
                    self.chamar_seguinte(content['data'])
                elif content['message'] == 'CANCELAR_CHAMADO':
                    self.cancelar_chamado(content['data'])
                elif content['message'] == 'FINALIZAR_ATENCAO':
                    self.finalizar_atencao(content['data'])
                elif content['message'] == 'INDICAR_AUSENCIA':
                    self.indicar_ausencia(content['data'])
                elif content['message'] == 'ATENDER':
                    self.atender(content['data'])
                elif content['message'] == 'DESOCUPAR_POSTO':
                    self.desocupar_posto(content['data'])
                elif content['message'] == 'GET_ESTADO':
                    self.get_estado()
                elif content['message'] == 'GET_POSTOS_INATIVOS':
                    self.get_postos_inativos(content['data'])


class FilaConsumer(JsonWebsocketConsumer):

    # Set to True if you want it, else leave it out
    strict_ordering = False
    http_user = True

    def connection_groups(self, **kwargs):
        return []

    def connect(self, message, **kwargs):
        if self.message.user.is_authenticated:
            super(FilaConsumer, self).connect(message, **kwargs)
            c = Cliente.get_from_user(self.message.user)
            grupo_cliente = c.get_grupo()
            grupo_cliente.add(self.message.reply_channel)
            self.get_estado()

    def get_estado(self, content={}):
        cliente = Cliente.get_from_user(self.message.user)
        cliente.get_estado()

    def entrar_na_fila(self, content):
        c = Cliente.get_from_user(self.message.user)
        t = c.entrar_na_fila(content['fila'], content['qrcode'])

    def sair_da_fila(self, content):
        c = Cliente.get_from_user(self.message.user)
        c.sair_da_fila(content['turno'])

    def receive(self, content, **kwargs):
        if self.message.user.is_authenticated:
            if content['message'] == 'ENTRAR_NA_FILA':
                self.entrar_na_fila(content['data'])
            elif content['message'] == 'SAIR_DA_FILA':
                self.sair_da_fila(content['data'])
            elif content['message'] == 'GET_ESTADO':
                self.get_estado(content['data'])

    def disconnect(self, message, **kwargs):
        if self.message.user.is_authenticated:
            PersistedGroup.remove_channel_from_groups(self.message.reply_channel)


class ScannerConsumer(JsonWebsocketConsumer):

    # Set to True if you want it, else leave it out
    strict_ordering = False
    http_user = True

    def connection_groups(self, **kwargs):
        return []

    def connect(self, message, **kwargs):
        if ( self.message.user.is_authenticated and
            self.message.user.has_perm('fila.habilitar_scanner') ):
                super(ScannerConsumer, self).connect(message, **kwargs)

    def scan(self, data):
        """
        Utilizado pelo scanner. Restringe o uso do codigo QR para o
        local onde pertence o scanner e envia as filas possiveis
        para o usuario.
        self.message.user é o scanner e deve ter as permissões necessarias.
        """
        qrcode = QRCode.objects.get(qrcode=data['qrcode'])
        cliente = Cliente.objects.get(username=qrcode.user.username)
        cliente.enviar_filas_disponiveis(qrcode, data['local'])

    def receive(self, content, **kwargs):
        if ( self.message.user.is_authenticated and
            self.message.user.has_perm('fila.habilitar_scanner') ):
            if content['message'] == 'SCAN':
                self.scan(content['data'])

    def disconnect(self, message, **kwargs):
        if ( self.message.user.is_authenticated and
            self.message.user.has_perm('fila.habilitar_scanner') ):
            PersistedGroup.remove_channel_from_groups(self.message.reply_channel)

