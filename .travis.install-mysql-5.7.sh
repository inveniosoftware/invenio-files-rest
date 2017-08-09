#!/usr/bin/env bash -e

if [ "$EXTRAS" = 'all,mysql' ]; then
  # echo mysql-apt-config mysql-apt-config/select-server select mysql-5.7 | sudo debconf-set-selections
  # wget http://dev.mysql.com/get/mysql-apt-config_0.7.3-1_all.deb
  # sudo dpkg --install mysql-apt-config_0.7.3-1_all.deb
  # sudo apt-get update -q
  # sudo apt-get install -q -y --allow-unauthenticated -o Dpkg::Options::=--force-confnew mysql-server
  # sudo service mysql restart
  # sudo mysql_upgrade
  # sudo service mysql restart

    export MYSQL_HOME="${HOME}/mysql-5.7.17-linux-glibc2.5-x86_64"
    cd ${HOME}
    wget http://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-5.7.17-linux-glibc2.5-x86_64.tar.gz
    echo "MYSQL DOWNLOAD OK"
    tar -xzf mysql-5.7.17-linux-glibc2.5-x86_64.tar.gz
    echo "MYSQL EXTRACT OK"
    cd $MYSQL_HOME
    echo "MYSQL CD OK"
    mkdir data
    mkdir log
cat > my.cnf <<EOF
[mysqld]
user=<userName>
EOF
cat > my.ini <<EOF
export BASE_DIR=${MYSQL_HOME}
export DATADIR=${MYSQL_HOME}/data
EOF
    echo "MYSQL CONF OK"

    $MYSQL_HOME/bin/mysqld --user=root --datadir=${MYSQL_HOME}/data \
        --basedir=$MYSQL_HOME  --log-error=$MYSQL_HOME/log/mysql.err \
        --pid-file=$MYSQL_HOME/mysql.pid --socket=$MYSQL_HOME/socket \
        --port=3306 --initialize
    echo "MYSQL INIT OK"
    $MYSQL_HOME/bin/mysqld --user=root --datadir=${MYSQL_HOME}/data \
        --basedir=$MYSQL_HOME  --log-error=$MYSQL_HOME/log/mysql.err \
        --pid-file=$MYSQL_HOME/mysql.pid --socket=$MYSQL_HOME/socket \
        --port=3306
    echo "MYSQL START OK"
fi
