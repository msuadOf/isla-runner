FROM ocaml/opam
USER root
RUN DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends  install zlib1g-dev pkg-config libgmp-dev z3 ca-certificates build-essential libgmp-dev z3 libz3-dev opam rsync pkg-config m4 sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
USER opam
RUN opam install sail