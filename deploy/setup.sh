#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo 'Run using: sudo bash deploy/setup.sh'
  exit 1
fi
cd "$(dirname "$0")/.."
if [[ "$PWD" != /var/www/ec2-registration ]]; then
  echo 'Place this project at /var/www/ec2-registration first (see README.md).'
  exit 1
fi
apt-get update
apt-get install -y apache2 libapache2-mod-wsgi-py3 python3 python3-pip python3-flask sqlite3
chown -R root:root /var/www/ec2-registration
find /var/www/ec2-registration -type d -exec chmod 755 {} +
find /var/www/ec2-registration -type f -exec chmod 644 {} +
install -d -o www-data -g www-data -m 700 /var/www/ec2-registration/instance
chown -R www-data:www-data /var/www/ec2-registration/instance
find /var/www/ec2-registration/instance -type f -exec chmod 600 {} +
sudo -u www-data python3 -c 'from app import create_app; create_app(); print("Database initialized")'
cp deploy/registration.conf /etc/apache2/sites-available/registration.conf
a2enmod wsgi
a2ensite registration
a2dissite 000-default
apache2ctl configtest
systemctl enable apache2
systemctl restart apache2
echo 'Ready. Open http://YOUR_EC2_PUBLIC_DNS/ in your browser.'
