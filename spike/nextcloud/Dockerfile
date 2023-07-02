FROM nextcloud:25.0.8-apache


RUN apt-get update; \
    apt -y install smbclient cifs-utils libsmbclient-dev make 

RUN pecl install smbclient