FROM debian:stretch-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
COPY requirements.txt entrypoint.sh /code/
RUN apt-get update && apt-get install --no-install-recommends --yes \
	python3-pip python3-setuptools python3-wheel libpython3.5-dev \
	gcc-6 gcc \
	libmariadbclient-dev \
	postgresql-common libpq-dev \
	gdal-bin \
	imagemagick mencoder
RUN apt-get install ffmpeg
RUN pip3 install -r /code/requirements.txt
RUN apt-get purge -y gcc-6 gcc \
	libmariadbclient-dev libpq-dev libpython3.5-dev && \
    apt-get autoremove -y && \
    apt-get clean

WORKDIR /code/SpiMediaGallery
ENTRYPOINT ["/code/entrypoint.sh"]
