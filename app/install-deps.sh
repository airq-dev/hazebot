set -eux

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get -y upgrade
apt-get -y install --no-install-recommends \
    gcc \
    g++ \
    libcurl4-openssl-dev \
    libpq-dev \
    libssl-dev \
    libz-dev \
    netcat \
    postgresql \
    postgresql-contrib \
    gdal-bin
apt-get clean
rm -rf /var/lib/apt/lists/*
