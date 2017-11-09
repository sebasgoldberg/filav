from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from channels import Group

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

    def pausar_atencao(self):
        self.posto.pausar_atencao()

    def finalizar_atencao(self):
        self.posto.finalizar_atencao()

    def desocupar_posto(self):
        self.posto.desocupar()

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

class Local(models.Model):

    nome = models.CharField(
        max_length=100,
        verbose_name=_('Nome'),
        unique=True
    )


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

    def get_grupo(self):
        return Group('fila-%s' % self.pk)

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
        posto.atender(turno)

        grupo_posto = posto.get_grupo().send({'message': 'ATENDER_TURNO'})
        turno.get_grupo().send({'message': 'IR_NO_POSTO'})
        self.get_grupo().send({'message': 'FILA_AVANCOU'})


class Turno(models.Model):

    INICIAL = 0
    NA_FILA = 1
    CANCELADO = 2
    NO_ATENDIMENTO = 3
    AUSENTE = 4
    ATENDIDO = 5

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
        return Group('turno-%s' % self.pk)

class Posto(models.Model):

    INATIVO = 0
    EM_PAUSA = 1
    ESPERANDO_CLIENTE = 2
    ATENDENDO = 3

    ESTADOS = (
        (INATIVO, _('Inativo')),
        (EM_PAUSA, _('Em pausa')),
        (ESPERANDO_CLIENTE, _('Esperando cliente')),
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
        blank=True
    )

    turno_em_atencao = models.ForeignKey(
        Turno,
        verbose_name=_('Turno em atencao'),
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    estado = models.IntegerField(choices=ESTADOS, default=INATIVO)

    class Meta:
        verbose_name = _("Posto")
        verbose_name_plural = _("Postos")

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

    def pausar_atencao(self):
        self.estado = Posto.EM_PAUSA
        self.save()

    def atender(self, turno):
        turno.estado = Turno.NO_ATENDIMENTO
        turno.save()
        self.estado = Posto.ATENDENDO
        self.turno_em_atencao = turno
        self.save()

    def finalizar_atencao(self):
        self.turno_em_atencao.estado = Turno.ATENDIDO
        self.turno_em_atencao.save()
        self.estado = Posto.EM_PAUSA
        self.turno_em_atencao = None
        self.save()

    def desocupar(self):
        self.estado = Posto.INATIVO
        self.funcionario = None
        self.save()
