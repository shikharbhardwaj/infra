FROM nextcloud:26.0.3-apache


RUN apt-get update; \
    apt -y install smbclient cifs-utils libsmbclient-dev make vim-tiny

RUN pecl install smbclient