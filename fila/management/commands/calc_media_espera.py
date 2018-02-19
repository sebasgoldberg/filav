from django.core.management.base import BaseCommand, CommandError

from django.utils import timezone as TZ
from datetime import timedelta as TD

from fila.models import Fila, SemTurnosParaCalcularMediaEspera, SemQtdMinTurnosParaCalcularMediaEspera

class Command(BaseCommand):
    help = 'Calcula a media de espera por fila.'

    def add_arguments(self, parser):
        parser.add_argument('--from', type=int, default=2*60*60, dest='from',
            help='A data desde que serão obtidos os turnos para realizar o calculo da media. '+
            'Inddicar a quantidade de segundos desde a data desde até a data atual. '+
            'Valor por default: 7200 (2 horas).')
        parser.add_argument('--to', type=int, default=0, dest='to',
            help='A data até que serão obtidos os turnos para realizar o calculo da media. '+
            'Inddicar a quantidade de segundos desde a data até, até a data atual. '+
            'Valor por default: 0 (a data atual).')
        parser.add_argument('--quan_min', type=int, default=None, dest='quan_min_turnos',
            help='Quantidade minima de turnos a obter para efetuar o calculo. '+
            'Casso não sejam encontrados turnos suficientes, não será realizado o calculo. '+
            'Valor por default: None (não tem minimo).')

    def handle(self, *args, **options):

        now = TZ.now()
        de = now - TD(seconds=options['from'])
        ate = now - TD(seconds=options['to'])
        qtd_min_turnos = options['quan_min_turnos']

        print(qtd_min_turnos)
        for fila in Fila.objects.all():
            try:
                fila.calcular_media_espera(de, ate, qtd_min_turnos)
                self.stdout.write(self.style.SUCCESS('Media de tempo de atendimento para fila %s: %s segundos' % (fila.nome, int(fila.media_espera))))
            except (SemQtdMinTurnosParaCalcularMediaEspera, SemTurnosParaCalcularMediaEspera) as e:
                self.stdout.write(self.style.WARNING('ADV: %s' % e))
