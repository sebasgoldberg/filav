FROM python:3
ENV PYTHONUNBUFFERED 1
RUN mkdir /filav
WORKDIR /filav
ADD requirements.txt /filav/
RUN pip install -r requirements.txt
ADD . /filav/
ENTRYPOINT [ "./docker-entrypoint.sh" ]
