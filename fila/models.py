from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from channels import Channel, Group

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

class Cliente(User):

    class Meta:
        proxy = True

    @staticmethod
    def get_from_user(user):
        return Cliente.objects.get(pk=user.pk)

    def entrar_na_fila(self, fila):
        turno = Turno.objects.create(
            fila=fila,
            cliente=self
        )
        fila.avancar()
        return turno

    def get_grupo(self):
        return PersistedGroup('cliente-%s' % self.pk)

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

        posto.get_grupo().send({'message': 'CLIENTE_CHAMADO'})

        tg = turno.get_grupo()
        tg.send({'message': 'IR_NO_POSTO'})

        fg = self.get_grupo()

        for channel in tg.channels:
            fg.discard(channel)

        fg.send({'message': 'FILA_AVANCOU'})

class TurnoAtivoManager(models.Manager):

    def get_queryset(self):
        return super(TurnoAtivoManager, self).get_queryset().filter(estado__in=Turno.ESTADOS_ATIVOS)

class Turno(models.Model):

    objects = models.Manager()
    ativos = TurnoAtivoManager()

    INICIAL = 0
    NA_FILA = 1
    CANCELADO = 2
    CLIENTE_CHAMADO = 3
    NO_ATENDIMENTO = 4
    AUSENTE = 5
    ATENDIDO = 6

    ESTADOS_ATIVOS = [
        NA_FILA,
        NO_ATENDIMENTO,
    ]

    ESTADOS = (
        (INICIAL, _('Inicial')),
        (NA_FILA, _('Na Fila')),
        (CANCELADO, _('Cancelado')),
        (NO_ATENDIMENTO, _('No Atendimento')),
        (AUSENTE, _('Ausente')),
        (ATENDIDO, _('Atendido')),
    )


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

    def indicar_ausencia(self):
        self.estado = Turno.AUSENTE
        self.save()
        tg = self.get_grupo()
        tg.send({'message': 'AUSENTE'})
        tg.discard_all()

    def atender(self):
        self.estado = Turno.NO_ATENDIMENTO
        self.save()
        tg = self.get_grupo()
        tg.send({'message': 'NO_ATENDIMENTO'})
        tg.discard_all()

class Posto(models.Model):

    INATIVO = 0
    EM_PAUSA = 1
    ESPERANDO_CLIENTE = 2
    CLIENTE_CHAMADO = 3
    ATENDENDO = 4

    ESTADOS = (
        (INATIVO, _('Inativo')),
        (EM_PAUSA, _('Em pausa')),
        (ESPERANDO_CLIENTE, _('Esperando cliente')),
        (CLIENTE_CHAMADO, _('Cliente chamado')),
        (ATENDENDO, _('Atendendo')),
    )

    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome'),
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

    turno_em_atencao = models.ForeignKey(
        Turno,
        verbose_name=_('Turno em atencao'),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False
    )

    estado = models.IntegerField(
        choices=ESTADOS,
        default=INATIVO,
        editable=False
        )

    class Meta:
        verbose_name = _("Posto")
        verbose_name_plural = _("Postos")

    def __str__(self):
        return '%s.%s' % (self.fila, self.nome)

    def get_grupo(self):
        return Group('posto-%s' % self.pk)

    def ocupar(self, funcionario):
        self.funcionario = funcionario
        self.estado = Posto.EM_PAUSA
        self.save()

    def chamar_seguinte(self):
        self.estado = Posto.ESPERANDO_CLIENTE
        self.save()
        self.fila.avancar()

    def cancelar_chamado(self):
        self.estado = Posto.EM_PAUSA
        self.save()

    def chamar_cliente(self, turno):
        turno.estado = Turno.CLIENTE_CHAMADO
        turno.save()
        self.estado = Posto.CLIENTE_CHAMADO
        self.turno_em_atencao = turno
        self.save()

    def atender(self):
        self.estado = Posto.ATENDENDO
        self.save()
        self.turno_em_atencao.atender()

    def indicar_ausencia(self):
        self.turno_em_atencao.indicar_ausencia()
        self.estado = Posto.EM_PAUSA
        self.turno_em_atencao = None
        self.save()

    def finalizar_atencao(self):
        self.turno_em_atencao.estado = Turno.ATENDIDO
        self.turno_em_atencao.save()
        self.turno_em_atencao.get_grupo().discard_all()
        self.estado = Posto.EM_PAUSA
        self.turno_em_atencao = None
        self.save()

    def desocupar(self):
        self.estado = Posto.INATIVO
        self.funcionario = None
        self.save()
