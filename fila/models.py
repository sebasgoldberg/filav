from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext as ugt
from django.contrib.auth.models import User

from channels import Channel, Group
from django.forms.models import model_to_dict

import json
import qrcode as qrlib
from django.utils import timezone as TZ

"""
 Media de tempo por local e fila:
En(x) = SUM(xi)/n
En+1(x) = SUM(xi)+xn+1/n+1 = SUM(xi)/n+1 + xn+1/n+1
SUM(xi)/n+1 = 1/(n/SUM(xi) + 1/SUM(xi)) = 1/(1/En + 1/n*En) = 1 / (n + 1) / n*En = n*En/(n+1) 
En+1(x) = SUM(xi)+xn+1/n+1 = SUM(xi)/n+1 + xn+1/n+1 = n*En/(n+1) + xn+1/n+1 # Calculado por local e por fila.
En+1(x) = n*En(x)/(n+1) + xn+1/n+1 # Calculo da media n+1 baseado na media En
Para realizar o calculo precisamos salvar por fila:
- E(x)
- n
E o mesmo deve ser feito ao finalizar o atendimento.

VARn(x) = E(x^2) - E(x)^2
En+1(x^2) = n*En(x^2)/(n+1) + xn+1^2/n+1 # Calculo da media n+1 do x^2 baseado na media En(x^2)
VARn+1(x) = n*En(x^2)/(n+1) + xn+1^2/n+1 - (n*En(x)/(n+1) + xn+1/n+1)^2

A partir de E(x) e VAR(x), pelo teorema central do limite, podemos obter um minimo e maximo de espera
Fixando uma determinada probabilidade para os limites obtidos.
Mas como a espera é uma sumatoria de esperanças, no limite do infinito a variança poderia ser despreciada.
Assim a espera poderia ser calculada como E(x)*#(turnos(fia))/#(postos) + E(x)
O ultimo termino é pela demora no posto que esta atendendo.
"""


class GroupChannels(models.Model):

    group_name = models.CharField(
        max_length=100,
        verbose_name=_('Grupo'),
    )

    channel_name = models.CharField(
        max_length=100,
        verbose_name=_('Canal'),
    )

    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('group_name', 'channel_name'))

class PersistedGroup(Group):

    def add(self, channel):
        super(PersistedGroup, self).add(channel)
        GroupChannels.objects.get_or_create(group_name=self.name,
            channel_name=channel.name)

    def discard(self, channel):
        super(PersistedGroup, self).discard(channel)
        try:
            gc = GroupChannels.objects.get(group_name=self.name,
                channel_name=channel.name)
            gc.delete()
        except PersistedGroup.DoesNotExist:
            pass

    @property
    def channels(self):
        for gc in GroupChannels.objects.filter(group_name=self.name):
            yield Channel(gc.channel_name)

    def discard_all(self):
        for c in [c for c in self.channels]:
            self.discard(c)

    @staticmethod
    def remove_channel_from_groups(channel):
        for gc in GroupChannels.objects.filter(channel_name=channel.name):
            PersistedGroup(gc.group_name).discard(channel)


class Funcionario(User):

    class Meta:
        proxy = True

    @staticmethod
    def get_from_user(user):
        return Funcionario.objects.get(pk=user.pk)

    def ocupar_posto(self, posto):
        posto.ocupar(self)

    def chamar_seguinte(self):
        self.posto.chamar_seguinte()

    def cancelar_chamado(self):
        self.posto.cancelar_chamado()

    def finalizar_atencao(self):
        self.posto.finalizar_atencao()

    def desocupar_posto(self):
        self.posto.desocupar()

    def indicar_ausencia(self):
        self.posto.indicar_ausencia()

    def atender(self):
        self.posto.atender()

    def get_grupo(self):
        return PersistedGroup('funcionario-%s' % self.pk)

class BaseDispatcher:

    def __init__(self, user):
        self.user = user

    def enviar_qrcode(self, qrcode):
        self.send({
            "message": "QR_CODE",
            "data":{
                "qrcode": qrcode,
            }
        })

    def enviar_filas_disponiveis(self, filas, qrcode):
        self.send({
            'message': 'FILAS_DISPONIBLES',
            'data':{
                'filas': filas,
                'qrcode': qrcode.qrcode,
            }
        })

    def enviar_turno(self, turno):
        self.send({
            'message': 'TURNO_ATIVO',
            'data': { 'turno': turno.to_dict(), }
        })


class ChannelsDispatcher(BaseDispatcher):

    def send(self, data):
        self.user.get_grupo().send({
            'text': json.dumps(data)
            })

from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TelegramDispatcher(BaseDispatcher):

    def __init__(self, *args, **kwargs):
        super(TelegramDispatcher, self).__init__(*args, **kwargs)
        self.bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)

    def _build_menu(self, buttons, n_cols, header_buttons=None,
        footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def enviar_qrcode(self, qrcode):
        img = qrlib.make(qrcode)
        bio = BytesIO()
        bio.name = 'image.jpeg'
        img.save(bio, 'JPEG')
        bio.seek(0)
        self.bot.send_photo(self.user.telegram.chat_id, photo=bio, 
            caption=_('Para entrar numa fila, por favor passar o codigo QR por algum dos scanners disponiveis.'))

    def enviar_filas_disponiveis(self, filas, qrcode):

        button_list = [
            InlineKeyboardButton(fila['nome'], callback_data='ENTRAR_NA_FILA %(fila)s %(qrcode)s' % {'fila':fila['id'], 'qrcode': qrcode.id}) for fila in filas
        ]
        reply_markup = InlineKeyboardMarkup(self._build_menu(button_list, n_cols=1))
        self.bot.send_message(self.user.telegram.chat_id,
             text=ugt("Por favor, selecionar a fila na que deseja entrar:"),
             reply_markup=reply_markup)

    def enviar_turno(self, turno):

        if turno.is_na_fila():
            button_list = [
                InlineKeyboardButton(ugt('Sair da fila'), callback_data='SAIR_DA_FILA %(turno)s' % {'turno':turno.id, }),
                InlineKeyboardButton(ugt('Atualizar'), callback_data='GET_ESTADO')
            ]
            reply_markup = InlineKeyboardMarkup(self._build_menu(button_list, n_cols=1))
            self.bot.send_message(self.user.telegram.chat_id,
                 text=ugt("Você esta na %(posicao)s° posição da fila %(fila)s." % {'posicao': turno.get_posicao(), 'fila': turno.fila.nome}),
                 reply_markup=reply_markup)
        elif turno.is_cliente_chamado():
            button_list = [
                InlineKeyboardButton(ugt('Sair da fila'), callback_data='SAIR_DA_FILA %(turno)s' % {'turno':turno.id, }),
                InlineKeyboardButton(ugt('Atualizar'), callback_data='GET_ESTADO')
            ]
            reply_markup = InlineKeyboardMarkup(self._build_menu(button_list, n_cols=1))
            self.bot.send_message(self.user.telegram.chat_id,
                 text=ugt("Você foi chamado!\nPor favor ir no posto %(posto)s." % {'posto':turno.posto.nome}),
                 reply_markup=reply_markup)
        elif turno.is_no_atendimento():
            button_list = [
                InlineKeyboardButton(ugt('Atualizar'), callback_data='GET_ESTADO')
            ]
            reply_markup = InlineKeyboardMarkup(self._build_menu(button_list, n_cols=1))
            self.bot.send_message(self.user.telegram.chat_id,
                 text=ugt("Você esta no atendimento do %(posto)s." % {'posto':turno.posto.nome}),
                 reply_markup=reply_markup)
        else:
            button_list = [
                InlineKeyboardButton(ugt('Entrar em outra fila'), callback_data='GET_ESTADO')
            ]
            reply_markup = InlineKeyboardMarkup(self._build_menu(button_list, n_cols=1))
            self.bot.send_message(self.user.telegram.chat_id,
                 text=ugt("Seu turno ficou com estado %(estado)s" % {'estado':turno.texto_estado()}),
                 reply_markup=reply_markup)



    def send(self, data):
        self.bot.send_message(chat_id=self.user.telegram.chat_id, text=json.dumps(data))


class Telegram(models.Model):

    user = models.OneToOneField(
        User,
        verbose_name=_('Usuario'),
        on_delete=models.CASCADE,
    )

    chat_id = models.CharField(
        max_length=100,
        verbose_name=_('Chat ID'),
        unique=True
    )


import telegram
from django.conf import settings

class Cliente(User):

    class Meta:
        proxy = True

    def is_channel_client(self):
        try:
            return self.telegram is None
        except Telegram.DoesNotExist:
            return True

    def __init__(self, *args, **kwargs):
        super(Cliente, self).__init__(*args, **kwargs)
        if self.is_channel_client():
            self.dispatcher = ChannelsDispatcher(self)
        else:
            self.dispatcher = TelegramDispatcher(self)

    @staticmethod
    def get_from_user(user):
        return Cliente.objects.get(pk=user.pk)

    def get_turno_ativo(self):
        return Turno.ativos.get(cliente=self)

    def get_grupo(self):
        return PersistedGroup('cliente-%s' % self.pk)

    def get_estado(self):
        try:
            self.enviar_turno_ativo()
        except Turno.DoesNotExist:
            self.enviar_qrcode()

    def entrar_na_fila(self, fila_id, qrcode_str):
        fila = Fila.objects.get(pk=fila_id)
        qrcode = QRCode.objects.get(qrcode=qrcode_str, user=self, local=fila.local)
        turno = Turno.objects.create(
            fila=fila,
            cliente=self
        )
        qrcode.delete()
        self.get_estado()
        fila.avancar()
        return turno

    def sair_da_fila(self, turno_id):
        t = Turno.objects.get(pk=turno_id, cliente=self)
        if t.is_cliente_chamado():
            posto = t.posto
            posto.indicar_ausencia()
            posto.chamar_seguinte()
        elif t.is_na_fila():
            t.cancelar()

    def enviar_turno_ativo(self, turno=None):
        if turno is None:
            turno = self.get_turno_ativo()
        self.dispatcher.enviar_turno(turno)

    def enviar_qrcode(self):
        qrcode, _ = QRCode.objects.get_or_create(user=self)
        self.dispatcher.enviar_qrcode(qrcode.qrcode)

    def enviar_filas_disponiveis(self, qrcode, local_id):
        local = Local.objects.get(pk=local_id)
        qrcode.local = local
        qrcode.save()
        filas = [ model_to_dict(f) for f in local.filas.all() ]
        self.dispatcher.enviar_filas_disponiveis(filas, qrcode)


class Local(models.Model):

    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome'),
        unique=True
    )

    def __str__(self):
        return self.nome


class Fila(models.Model):

    local = models.ForeignKey(
        Local,
        verbose_name=_('Local'),
        on_delete=models.PROTECT,
        related_name='filas'
    )

    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome'),
    )

    class Meta:
        verbose_name = _("Fila")
        verbose_name_plural = _("Filas")
        unique_together = (("local", "nome"),)

    def __str__(self):
        return '%s.%s' % (self.local, self.nome)

    def get_grupo(self):
        return PersistedGroup('fila-%s' % self.pk)

    def proximo_turno(self):
        return self.turnos.filter(estado=Turno.NA_FILA
            ).order_by('creation_date').first()

    def avancar(self):
        turno = self.proximo_turno()
        if turno is None:
            return
        posto = self.postos.filter(estado=Posto.ESPERANDO_CLIENTE).first()
        if posto is None:
            return
        posto.chamar_cliente(turno)
        for turno_na_fila in Turno.ativos.filter(fila=self):
            if turno_na_fila.pk == turno.pk:
                continue
            turno_na_fila.notificar()


class TurnoAtivoManager(models.Manager):

    def get_queryset(self):
        return super(TurnoAtivoManager, self).get_queryset().filter(estado__in=Turno.ESTADOS_ATIVOS)

class TurnoNaFilaManager(models.Manager):

    def get_queryset(self):
        return super(TurnoNaFilaManager, self).get_queryset().filter(estado=Turno.NA_FILA)

class Turno(models.Model):

    objects = models.Manager()
    ativos = TurnoAtivoManager()
    na_fila = TurnoNaFilaManager()

    INICIAL = 0
    NA_FILA = 1
    CANCELADO = 2
    CLIENTE_CHAMADO = 3
    NO_ATENDIMENTO = 4
    AUSENTE = 5
    ATENDIDO = 6

    ESTADOS_ATIVOS = [
        NA_FILA,
        CLIENTE_CHAMADO,
        NO_ATENDIMENTO,
    ]

    ESTADOS = (
        (INICIAL, ugt('Inicial')),
        (NA_FILA, ugt('Na Fila')),
        (CANCELADO, ugt('Cancelado')),
        (CLIENTE_CHAMADO, ugt('Ir no posto')),
        (NO_ATENDIMENTO, ugt('No Atendimento')),
        (AUSENTE, ugt('Ausente')),
        (ATENDIDO, ugt('Atendido')),
    )

    ESTADOS_DICT = dict(ESTADOS)

    fila = models.ForeignKey(
        Fila,
        verbose_name=_('Fila'),
        on_delete=models.PROTECT,
        related_name='turnos',
    )

    cliente = models.ForeignKey(
        Cliente,
        verbose_name=_('Cliente'),
        on_delete=models.PROTECT,
        related_name='turnos',
    )

    creation_date = models.DateTimeField(auto_now_add=True)

    last_modification = models.DateTimeField(auto_now=True)

    estado = models.IntegerField(choices=ESTADOS, default=NA_FILA)

    cliente_chamado_date = models.DateTimeField(null=True, editable=False)

    def save(self, *args, **kwargs):
        if self.is_cliente_chamado() and self.cliente_chamado_date is None:
            self.cliente_chamado_date = TZ.now()
        return super(Turno, self).save(*args, **kwargs)

    def is_na_fila(self):
        return self.estado == Turno.NA_FILA

    def is_cliente_chamado(self):
        return self.estado == Turno.CLIENTE_CHAMADO

    def is_no_atendimento(self):
        return self.estado == Turno.NO_ATENDIMENTO

    def get_grupo(self):
        return PersistedGroup('turno-%s' % self.pk)

    def cancelar(self):
        self.estado = Turno.CANCELADO
        self.save()
        tg = self.get_grupo()
        fg = self.fila.get_grupo()
        for channel in [x for x  in tg.channels]:
            tg.discard(channel)
            fg.discard(channel)
        self.notificar()

    def finalizar_atencao(self):
        self.estado = Turno.ATENDIDO
        self.save()
        self.notificar()

    def indicar_ausencia(self):
        self.estado = Turno.AUSENTE
        self.save()
        self.notificar()

    def atender(self):
        self.estado = Turno.NO_ATENDIMENTO
        self.save()
        self.notificar()

    def chamar_cliente(self):
        self.estado = Turno.CLIENTE_CHAMADO
        self.save()
        self.notificar()

    def get_posicao(self):
        if self.estado != Turno.NA_FILA:
            return 0
        i = 0
        for x in Turno.na_fila.filter(fila=self.fila).order_by('creation_date'):
            i = i + 1
            if self.pk == x.pk:
                break
        return i   

    def texto_estado(self):
        return Turno.ESTADOS_DICT[self.estado]

    def to_dict(self):
        turno_dict = model_to_dict(self)
        turno_dict['fila'] = model_to_dict(self.fila)
        turno_dict['fila']['local'] = model_to_dict(self.fila.local)
        turno_dict['posicao'] = self.get_posicao()
        turno_dict['texto_estado'] = self.texto_estado()
        turno_dict['creation_date'] = str(self.creation_date)
        try:
            turno_dict['posto'] = model_to_dict(self.posto)
        except Posto.DoesNotExist:
            pass
        return turno_dict

    def notificar(self):
        if self.cliente:
            self.cliente.enviar_turno_ativo(self)


class Posto(models.Model):

    INATIVO = 0
    EM_PAUSA = 1
    ESPERANDO_CLIENTE = 2
    CLIENTE_CHAMADO = 3
    ATENDENDO = 4

    ESTADOS = (
        (INATIVO, ugt('Inativo')),
        (EM_PAUSA, ugt('Em pausa')),
        (ESPERANDO_CLIENTE, ugt('Esperando cliente')),
        (CLIENTE_CHAMADO, ugt('Cliente chamado')),
        (ATENDENDO, ugt('Atendendo')),
    )

    ESTADOS_DICT = dict(ESTADOS)

    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome'),
    )

    local = models.ForeignKey(
        Local,
        verbose_name=_('Local'),
        on_delete=models.CASCADE,
        related_name='postos'
    )

    fila = models.ForeignKey(
        Fila,
        verbose_name=_('Fila'),
        on_delete=models.PROTECT,
        related_name='postos',
    )

    funcionario = models.OneToOneField(
        Funcionario,
        verbose_name=_('Funcionario'),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False
    )

    turno_em_atencao = models.OneToOneField(
        Turno,
        verbose_name=_('Turno em atencao'),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    estado = models.IntegerField(
        choices=ESTADOS,
        default=INATIVO,
        )

    class Meta:
        verbose_name = _("Posto")
        verbose_name_plural = _("Postos")
        permissions = (
            ('atender_clientes', 'Pode ocupar um posto e atender os clientes.'),
        )

    def __str__(self):
        return '%s.%s' % (self.fila, self.nome)

    def notificar(self):
        if self.funcionario:
            self.funcionario.get_grupo().send({
                'text': json.dumps({
                    'message': 'POSTO',
                    'data': { 'posto': self.to_dict(), }
                })})

    def get_grupo(self):
        return Group('posto-%s' % self.pk)

    def ocupar(self, funcionario):
        self.funcionario = funcionario
        self.estado = Posto.EM_PAUSA
        self.save()
        self.notificar()

    def chamar_seguinte(self):
        self.estado = Posto.ESPERANDO_CLIENTE
        self.save()
        self.notificar()
        self.fila.avancar()

    def cancelar_chamado(self):
        self.estado = Posto.EM_PAUSA
        self.save()
        self.notificar()

    def chamar_cliente(self, turno):
        self.estado = Posto.CLIENTE_CHAMADO
        self.turno_em_atencao = turno
        self.save()
        turno.chamar_cliente()
        self.notificar()

    def atender(self):
        self.estado = Posto.ATENDENDO
        self.save()
        self.turno_em_atencao.atender()
        self.notificar()

    def indicar_ausencia(self):
        self.turno_em_atencao.indicar_ausencia()
        self.estado = Posto.EM_PAUSA
        self.turno_em_atencao = None
        self.save()
        self.notificar()

    def finalizar_atencao(self):
        self.turno_em_atencao.finalizar_atencao()
        self.estado = Posto.EM_PAUSA
        self.turno_em_atencao = None
        self.save()
        self.notificar()

    def desocupar(self):
        self.estado = Posto.INATIVO
        self.notificar()
        self.funcionario = None
        self.save()

    def texto_estado(self):
        return Posto.ESTADOS_DICT[self.estado]

    def to_dict(self):
        posto_dict = model_to_dict(self)
        posto_dict['local'] = model_to_dict(self.local)
        posto_dict['fila'] = model_to_dict(self.fila)
        if self.turno_em_atencao:
            posto_dict['turno_em_atencao'] = model_to_dict(
                self.turno_em_atencao)
            posto_dict['turno_em_atencao']['cliente'] = {
                'name': self.turno_em_atencao.cliente.username
                }
        posto_dict['texto_estado'] = self.texto_estado()
        posto_dict['estado'] = self.estado
        posto_dict['funcionario'] = { 'name': self.funcionario.username }
        return posto_dict

import hashlib
import time

def gerar_codigo_qr():
    h = hashlib.sha1()
    h.update(str(time.time()).encode('utf-8'))
    return h.hexdigest()

class QRCode(models.Model):

    class Meta:
        permissions = (
            ('habilitar_scanner', 'Pode habilitar scanners de codigos QR para acessar a fila virtual.'),
        )

    user = models.OneToOneField(
        User,
        verbose_name=_('Usuario'),
        on_delete=models.CASCADE,
    )

    qrcode = models.CharField(
        max_length=100,
        verbose_name=_('Codigo QR'),
        default = gerar_codigo_qr
    )

    local = models.ForeignKey(
        Local,
        verbose_name=_('Local'),
        on_delete=models.CASCADE,
        null=True
    )

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.qrcode = '%s@%s' % (gerar_codigo_qr(), self.user.username)
        return super(QRCode, self).save(*args, **kwargs)


