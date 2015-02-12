#!/bin/sh

if [ `id -u` -ne "0" ]
then
    echo "E: Please run this script as root"
    exit 1
fi

#clean envirment
service apache2 stop
rm -rf /usr/local/bin/cps*
rm -rf /etc/cpsdirector
rm -rf /usr/local/lib/python2.7/dist-packages/cpslib*
rm -rf /usr/local/lib/python2.7/dist-packages/cpsdirector*
rm -rf /etc/apache2/sites-available/conpaas-director.conf
rm -rf /etc/apache2/sites-enabled/conpaas-director.conf
rm -rf /var/www/*


cd ./cpsdirector-1.4.2/

#Generate configuration files
python getconf.py

chown -R ubuntu. director.cfg.example

# Installing required Debian packages
apt-get update
apt-get -y --force-yes install build-essential python-setuptools python-dev apache2 libapache2-mod-wsgi libcurl4-openssl-dev ntpdate lynx moreutils

# Reinstalling setuptools (fixes a bug on some upgrade installations)
apt-get -y --force-yes --reinstall install python-setuptools

# Set correct date and time
ntpdate 0.us.pool.ntp.org

# Installing cpsdirector
python setup.py install

# install memcache
apt-get install -y memcached python-memcache

# Configuring SSL certificates
cpsconf.py

# Configuring Apache
a2enmod wsgi
a2enmod ssl
a2ensite conpaas-director.conf

# Installing required Debian packages
apt-get -y --force-yes install libapache2-mod-php5 php5-curl

cd ../cpsfrontend-1.4.2/

# Copying the www directory underneath the web server document root
cp -a www/ /var/

# Copy conf/main.ini and conf/welcome.txt in the ConPaaS Director configuration folder
# (if these are not already there)
if [ ! -e "/etc/cpsdirector/main.ini" ] ; then
    cp conf/main.ini /etc/cpsdirector/
fi
if [ ! -e "/etc/cpsdirector/welcome.txt" ] ; then
    cp conf/welcome.txt /etc/cpsdirector/
fi

# Configuring Apache
a2enmod ssl
a2ensite default-ssl

# Restarting apache
service apache2 restart

cd ../
