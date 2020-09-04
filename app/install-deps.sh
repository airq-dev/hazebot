set -eux

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get -y upgrade
apt-get -y install --no-install-recommends \
    gcc libz-dev libmemcached-dev
apt-get clean
rm -rf /var/lib/apt/lists/*