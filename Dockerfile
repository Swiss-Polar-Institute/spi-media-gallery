FROM debian:stretch-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
RUN apt-get update && apt-get install --no-install-recommends --yes \
	python3-pip python3-setuptools python3-wheel libpython3.5-dev \
	gcc-6 gcc \
	libmariadbclient-dev \
	postgresql-common libpq-dev \
	gdal-bin
COPY requirements.txt entrypoint.sh /code/
RUN pip3 install -r /code/requirements.txt

WORKDIR /code/SpiMediaGallery
ENTRYPOINT ["/code/entrypoint.sh"]
