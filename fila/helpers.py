from django.contrib.auth.models import User
from .models import *
from django.contrib.auth.models import Permission

def get_or_create_funcionario_scanner(username='s1'):
    f = get_or_create_funcionario(username)
    p = Permission.objects.get(codename='habilitar_scanner')
    f.user_permissions.add(p)
    return f

def get_or_create_funcionario_posto(username='p1'):
    f = get_or_create_funcionario(username)
    p = Permission.objects.get(codename='atender_clientes')
    f.user_permissions.add(p)
    return f

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
    posto, _ = Posto.objects.get_or_create(nome=reg[POSTO], fila=fila, local=local)
    return posto


def get_or_create_cliente(username='c1'):
    try:
        return Cliente.objects.get(username=username)
    except Cliente.DoesNotExist:
        pass
    User.objects.create_user(username=username)
    return Cliente.objects.get(username=username)


def get_first_and_last_name(name):
    names = name.split(',', 1)
    if len(names) == 0:
        return ('','')
    if len(names)==1:
        return ('', names[0].strip()[0:30])
    return (names[1].strip()[0:30], names[0].strip()[0:30])

def clean_user_data(model_fields):
    """
    Transforms the user data loaded from
    LDAP into a form suitable for creating a user.
    """
    model_fields['first_name'], model_fields['last_name'] = get_first_and_last_name(
        model_fields.get('first_name',''))
    return model_fields

def get_or_create_qrcode(user, fila):

    qrcode, _ = QRCode.objects.get_or_create(user=user)
    qrcode.local = fila.local
    qrcode.save()
    return qrcode
