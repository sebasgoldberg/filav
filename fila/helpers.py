from django.contrib.auth.models import User
from .models import *

def get_or_create_funcionario_scanner(username='s1'):
    return get_or_create_funcionario(username)

def get_or_create_funcionario(username='f1'):
    try:
        return Funcionario.objects.get(username=username)
    except Funcionario.DoesNotExist:
        pass
    User.objects.create_user(username=username)
    return Funcionario.objects.get(username=username)

def get_or_create_local(nome='l1'):
    local, _ = Local.objects.get_or_create(nome=nome)
    return local

def get_or_create_posto(reg=['l1', 'f1', 'p1']):
    LOCAL = 0
    FILA = 1
    POSTO = 2
    local = get_or_create_local(reg[LOCAL])
    fila, _ = Fila.objects.get_or_create(nome=reg[FILA], local=local)
    posto, _ = Posto.objects.get_or_create(nome=reg[POSTO], fila=fila)
    return posto


def get_or_create_cliente(username='c1'):
    try:
        return Cliente.objects.get(username=username)
    except Cliente.DoesNotExist:
        pass
    User.objects.create_user(username=username)
    return Cliente.objects.get(username=username)


