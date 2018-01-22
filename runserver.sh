
if [ -x $PRIVATE_KEY_FILE ]
then
  PRIVATE_KEY_FILE=crt/privkey.pem
fi

if [ -x $CERT_KEY_FILE ]
then
  CERT_KEY_FILE=crt/fullchain.pem
fi

if [ -x $SSL_PORT ]
then
    SSL_PORT=443
fi

./manage.py runworker &
RUNWORKER_PID="$!"

daphne -e ssl:${SSL_PORT}:privateKey=${PRIVATE_KEY_FILE}:certKey=${CERT_KEY_FILE} filav.asgi:channel_layer &
DAPHNE_PID="$!"
