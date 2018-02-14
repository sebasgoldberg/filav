from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User

from telegram.ext import Updater
from telegram.ext import CommandHandler
import logging

from fila.models import Telegram, Cliente


def get_cliente_from_chat_id(chat_id):
    telegram = None
    try:
        telegram = Telegram.objects.get(chat_id=chat_id)
    except Telegram.DoesNotExist:
        user = User.objects.create_user(username=chat_id)
        telegram = Telegram.objects.create(user=user, chat_id=chat_id)
    return Cliente.get_from_user(telegram.user)

def start(bot, update):
    atualizar(bot, update)

def atualizar(bot, update):
    cliente = get_cliente_from_chat_id(update.message.chat_id)
    cliente.get_estado()

def entrar(bot, update, args):
    cliente = get_cliente_from_chat_id(update.message.chat_id)
    cliente.entrar_na_fila(args[0], args[1])

def sair(bot, update, args):
    cliente = get_cliente_from_chat_id(update.message.chat_id)
    cliente.sair_da_fila(args[0])

class Command(BaseCommand):
    help = 'Executa o bot do telegram para fila virtual'

    def add_arguments(self, parser):
        #parser.add_argument('poll_id', nargs='+', type=int)
        pass

    def handle(self, *args, **options):

        #raise CommandError('Poll "%s" does not exist' % poll_id)
        #self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % poll_id))

        updater = Updater(token=settings.TELEGRAM_BOT_TOKEN)

        dispatcher = updater.dispatcher

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO)
        dispatcher.add_handler(CommandHandler('atualizar', atualizar))
        dispatcher.add_handler(CommandHandler('entrar', entrar, pass_args=True))
        dispatcher.add_handler(CommandHandler('sair', sair, pass_args=True))

        updater.start_polling()
        updater.idle()
        updater.stop()
