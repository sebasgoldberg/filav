from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User

from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackQueryHandler
import logging

from fila.models import Telegram, Cliente, QRCode


def get_cliente_from_chat_id(chat_id, user=None):
    telegram = None
    try:
        telegram = Telegram.objects.get(chat_id=chat_id)
    except Telegram.DoesNotExist:
        user = User.objects.create_user(username=chat_id)
        telegram = Telegram.objects.create(user=user, chat_id=chat_id)
    if user:
        telegram.user.first_name=user.first_name
        telegram.user.last_name=user.last_name
        telegram.user.save()
    
    return Cliente.get_from_user(telegram.user)

def start(bot, update):
    atualizar(bot, update)

def atualizar(bot, update):
    user = update.message.from_user
    cliente = get_cliente_from_chat_id(update.message.chat_id, user)
    cliente.get_estado()

def entrar(bot, update, args):
    cliente = get_cliente_from_chat_id(update.message.chat_id)
    cliente.entrar_na_fila(args[0], args[1])

def sair(bot, update, args):
    cliente = get_cliente_from_chat_id(update.message.chat_id)
    cliente.sair_da_fila(args[0])

def query_handler(bot, update, *args, **optional_args):
    cliente = get_cliente_from_chat_id(update.callback_query.message.chat.id)
    callback_data = update.callback_query.data
    parts = callback_data.split(' ')
    command = parts[0]
    if command == "ENTRAR_NA_FILA":
        qrcode = QRCode.objects.get(pk=parts[2])
        cliente.entrar_na_fila(parts[1], qrcode.qrcode)
    elif command == "SAIR_DA_FILA":
        cliente.sair_da_fila(parts[1])
    elif command == "GET_ESTADO":
        cliente.get_estado()

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
        dispatcher.add_handler(CommandHandler('start', start))
        dispatcher.add_handler(CommandHandler('atualizar', atualizar))
        dispatcher.add_handler(CommandHandler('entrar', entrar, pass_args=True))
        dispatcher.add_handler(CommandHandler('sair', sair, pass_args=True))
        dispatcher.add_handler(CallbackQueryHandler(callback=query_handler, pass_user_data=True))

        updater.start_polling()
        updater.idle()
        updater.stop()
