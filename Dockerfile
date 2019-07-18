FROM debian:stretch-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code
RUN apt-get update && apt-get install --no-install-recommends --yes \
	python3-pip python3-setuptools python3-wheel libpython3.5-dev \
	gcc-6 gcc \
	libmariadbclient-dev \
	postgresql-common libpq-dev \
	gdal-bin
RUN pip3 install -r requirements.txt
COPY ./entrypoint.sh /code
ENTRYPOINT ["/code/entrypoint.sh"]
