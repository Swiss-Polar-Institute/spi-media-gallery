FROM debian:buster-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
COPY requirements.txt entrypoint.sh /code/
RUN apt-get update && apt-get install --no-install-recommends --yes \
	python3-pip python3-setuptools python3-wheel libpython3.7-dev \
	gcc-7 gcc \
	libmariadbclient-dev libmariadb-dev-compat \
	libmariadb3 \
	postgresql-common libpq-dev \
	gdal-bin \
	imagemagick mencoder
RUN apt-get install ffmpeg
RUN pip3 install -r /code/requirements.txt
RUN apt-get purge -y gcc-6 gcc \
	libmariadbclient-dev libpq-dev libpython3.5-dev && \
	gdal-bin && \
    pip3 install -r /code/requirements.txt && \
    apt-get purge -y gcc-7 gcc \
	libmariadbclient-dev libmariadb-dev-compat libpq-dev libpython3.7-dev && \
    apt-get autoremove -y && \
    apt-get clean

WORKDIR /code/SpiMediaGallery
ENTRYPOINT ["/code/entrypoint.sh"]
