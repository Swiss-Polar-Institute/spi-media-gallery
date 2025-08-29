FROM python:3.10.6-slim-bullseye

# ----------------------------------------------------------------------------------------------------------------------
# Environment variables
# ----------------------------------------------------------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ----------------------------------------------------------------------------------------------------------------------
# Install utility software
# ----------------------------------------------------------------------------------------------------------------------
RUN apt-get update && apt-get install --no-install-recommends --yes \
  gcc \
  libmariadb-dev-compat \
  libmariadb3 mariadb-client \
  gdal-bin \
  imagemagick ffmpeg libmediainfo0v5 exiftool libjpeg-progs \
  libexempi8 \
  netcat

ADD https://www.dechifro.org/dcraw/dcraw.c /tmp/
RUN gcc -o /usr/bin/dcraw -O4 /tmp/dcraw.c -lm -DNODEPS
RUN rm /tmp/dcraw.c
# Some photos are bigger than the ImageMagick default size (16KP width and height)
# and 1 GiB for disk cache
# Here we change the limits
RUN sed -i 's/<policy domain="resource" name="width" value="[0-9]\+KP"\/>/<policy domain="resource" name="width" value="64KP"\/>/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="resource" name="height" value="[0-9]\+KP"\/>/<policy domain="resource" name="height" value="64KP"\/>/' /etc/ImageMagick-6/policy.xml  && \
    sed -i 's/<policy domain="resource" name="disk" value="[0-9]\+GiB"\/>/<policy domain="resource" name="disk" value="4GiB"\/>/' /etc/ImageMagick-6/policy.xml

# ----------------------------------------------------------------------------------------------------------------------
# Clean-up
# ----------------------------------------------------------------------------------------------------------------------
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code

# ----------------------------------------------------------------------------------------------------------------------
# Install requiement
# ----------------------------------------------------------------------------------------------------------------------
RUN python -m pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# ----------------------------------------------------------------------------------------------------------------------
# Add entrypoint
# ----------------------------------------------------------------------------------------------------------------------
COPY ./entrypoint.prod.sh /code/entrypoint.prod.sh
RUN chmod +x /code/entrypoint.prod.sh

COPY . .

ENTRYPOINT ["/code/entrypoint.prod.sh"]
