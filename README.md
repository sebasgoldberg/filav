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

#### Estados

A continuação ficam definidos os estados em que poderia estar um posto e as operações
a realizar para transitar de um estado a outro.

![Diagrama de Estados Posto][estados_posto]

[estados_posto]: https://raw.githubusercontent.com/sebasgoldberg/filav/master/docs/estados-postos.png "Diagrama de Estados Postos"

A continuação ficam definidos os estados em que poderia estar um cliente e as operações
a realizar para transitar de um estado a outro.


### Frontend

#### App de Cliente

Nesta app o cliente poderá realizar as seguintes operações:
- Registro de cliente.
- Login de cliente.
- Gerar codigo QR.
- Entrar na fila.
- Sair da fila.
- Receber notificações.

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
