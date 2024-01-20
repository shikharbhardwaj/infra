FROM ghcr.io/linuxserver/baseimage-ubuntu:jammy-version-d74de700

RUN apt-get update && apt-get install -y --no-install-recommends tini wget \
    vim-gtk zsh tmux git build-essential sudo openssh-client python3 \
    coreutils && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/tsl0922/ttyd/releases/download/1.7.4/ttyd.i686 -O /usr/bin/ttyd
RUN chmod +x /usr/bin/ttyd

RUN useradd -rm --create-home -s /bin/zsh -g 1000 -G sudo -u 1000 appuser
USER appuser
WORKDIR /home/appuser
ENV HOME /home/appuser

RUN git clone https://github.com/shikharbhardwaj/dotfiles
RUN /home/appuser/dotfiles/install

EXPOSE 7681

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["ttyd", "-W", "zsh"]