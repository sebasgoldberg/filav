# Fila Virtual

## Introdução

O objetivo principal desta solução é fazer com que o cliente consiga minimizar o tempo de espera na fila e possa se concentrar no que realmente importa para ele: comprar.

Adicionalmente será possivel:
- Associar uma venda especifica realizada no PDV com o cliente que esteja fazendo a compra.
- Medir a eficiência do atendimento nos PDVs.

## Apps Involucradas

### Backend

Implementado utilizando Django Channels.

Responsavel por coordinar a interação entre as apps de cliente, scanner e posto em tempo real.

### Frontend

#### App de Cliente

Nesta app o cliente poderá realizar as seguintes operações:
- Registro de cliente.
- Login de cliente.
- Gerar codigo QR.
- Entrar na fila.
- Sair da fila.
- Visualização
    - do tempo de espera uma vez que entrou na fila.
    - da posição que tem na fila.
- Receber notificações:
    - Mudança de estados do turno.
    - Modificação do tempo de espera e/ou posição.

#### Scanner

Para assegurar que o cliente esta fisicamente na loja, á mesma contará com uma
app que faz o scann do codigo QR gerado na App de Cliente, otorgando autorização
para entrar na fila.

As operações possiveis de serem realizadas são as seguintes:
- Login de usuario.
- Seleção da loja.
- Scann.

#### App de Posto
Nesta app o funcionario que esteja no posto podera realizar as seguintes operações:
- Login de usuario.
- Ocupar posto.
- Desocupar posto.
- Chamar seguinte cliente.
- Pausar atenção.
- Finalizar atenção.
- Indicar ausencia do cliente.

## Deploy com Docker
- `git clone --recursive https://github.com/sebasgoldberg/filav.git`
- `cd filav`
- `cp web-variables.default.env web-variables.env` (editar o novo arquivo conforme suas necesidades).
- `docker build -t filav .`
- `mkdir crt` e colocar o certificado e a chave privada a utilizar com o daphne (HTTP/WebSocket Server).
  O nome do certificado deve ser fullchain.pem e o nome da chave privada deve ser privkey.pem.
- `docker-compose up`

## Instalação (sem Docker)

### Requisitos
- Ter um servidor Redis instalado: `sudo apt-get install redis-server`
- Ter um servidor LDAP (Opcional, em caso de querer fazer login utilizando alguma conta corporativa).
- Configurar a autenticação por facebook (Opcional).
- Ter instalado python3
- Ter virtualenv (Recomendado).
- Ter instalado postgresql (Recomendado): `sudo apt-get install postgresql-x.x`

### Procedimento
- `git clone --recursive https://github.com/sebasgoldberg/filav.git`
- `cd filav`
- Criar o banco de dados.
- Criar um script setenv (Tomar como exemplo o arquivo setenv.default).
- Realizar as mudanças pertinentes no settings.py (Utilização de outro banco de dados, etc.).
- Criar o virtualenv: `.mkvirtualenv --python=$(which python3) filav`.
- Instalar as dependencias: `pip install -r requirements.txt`
- Executar setenv: `source setenv.sh`
- Aplicar as migrações ao banco de dados: `./manage.py migrate`
- Executar a aplicação: `./manage.py runserver` ou `source runserver.sh`

### Cron Jobs

#### Calculo de Media de Tempo de Atendimento
O calculo da media de tempo de atendimento é necessario para estimar o tempo de espera até ser atendido por cada fila.
O calculo é baseado nos tempos de demora desde que foi chamado cada cliente até que foi atendido ou marcado como ausente, por isso o calculo é baseado nas informações obtidas a partir de cada turno.
O calculo da media é realizado por fila.
O comando para calcular a media é `./manage.py calc_media_espera` que por default realizará o calculo para todos os turnos completados nas ultimas duas horas.
Para ver um detalhe dos parametros possiveis por favor executar `./manage.py help calc_media_espera`.
É recomendavel executar este comando como um job cron. Uma possivel entrada para executar cada 15 minutos o calculo para todos os turnos acontecidos no ultimo dia e realizando a integração com journald:

```
*/15 * * * * (cd <path ao projeto> && source <path ao venv>/bin/activate && source ./setenv.sh && ./manage.py calc_media_espera --from 84600) 2>&1 | systemd-cat -t 'filav.calc_media_espera'
```

## Considerações

- A utilização de HTTPS é necesaria para conseguir utilizar a camera do scanner no navegador web.
- Se o certificado não fosse de confiança, então o web socket, em geral não funcionara em dispositivos mobiles.

## Alguns Diagramas

### Diagramas de Estado de um Posto

A continuação ficam definidos os estados em que poderia estar um posto e as operações
a realizar para transitar de um estado a outro.

![Diagrama de Estados Posto][estados_posto]

[estados_posto]: https://raw.githubusercontent.com/sebasgoldberg/filav/master/docs/estados-postos.png "Diagrama de Estados Postos"

### Diagrama de Estados de um Turno

A continuação ficam definidos os estados em que poderia estar um turno e as operações
a realizar para transitar de um estado a outro.

![Diagrama de Estados Turno][estados_turno]

[estados_turno]: https://raw.githubusercontent.com/sebasgoldberg/filav/master/docs/estados-turnos.png "Diagrama de Estados Turno"

### Diagrama de Sequencia da Validação Presencial do Cliente na Loja Antes de Acessar numa Fila

A continuação fica definida a sequencia que valida que o cliente esteja presencialmente na loja
sem necessidade de utilizar serviços de localização.
Basicamente a ideia é gerar um codigo QR unico no dispositivo do cliente, e escanear o mesmo em
algum scanner da loja.

![Diagrama de Sequencia Ingresso][sequencia_ingresso]

[sequencia_ingresso]: https://raw.githubusercontent.com/sebasgoldberg/filav/master/docs/sequencia-ingresso.png "Diagrama de Sequencia Ingresso"


