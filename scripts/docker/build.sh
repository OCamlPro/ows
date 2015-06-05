#!/bin/bash

cat <<EOF > ows.conf
BASEDIR=/home/ows/ows
VERSIONS="${VERSIONS:-"4.02.1 4.01.0 4.02.0 4.00.1 3.12.1"}"

DISTCHECK=/home/ows/dose/distcheck.native

OPAM=/home/ows/opam/src/opam
OPAMOPTIONS="--use-internal-solver"

OWSRUN=/home/ows/ows/ows-run
OWSARCHIVE=/home/ows/ows/ows-archive
OWSUPDATE=/home/ows/ows/ows-update

REPORTDIR=${BASEDIR}/reports

DATADIR=${BASEDIR}/repository

TMPDIR=/home/ows/tmp

TARGETDIR=${BASEDIR}/html

BASEURL=http://localhost:8000
EOF

GITCLONE=$RANDOM-gitclone.sh
cat <<EOF > Dockerfile
FROM debian:jessie
MAINTAINER Pietro Abate <pietro.abate@pps.univ-paris-diderot.fr>

RUN echo "deb http://ftp.ens-cachan.fr/ftp/debian/ unstable main" > /etc/apt/sources.list
RUN apt-get update

RUN apt-get install --no-install-recommends --yes \
  vim \
  less \
  build-essential \
  unzip \
  rsync \
  m4 \
  git \
  curl \
  ca-certificates \
  python-matplotlib \
  python-pydot \
  python-progressbar \
  python-jinja2 \
  ocaml \
  cppo \
  libcudf-ocaml-dev \
  libocamlgraph-ocaml-dev \
  libextlib-ocaml-dev \
  libbz2-ocaml-dev \
  libre-ocaml-dev

RUN useradd -c 'ows' -m -d /home/ows -s /bin/bash ows
USER ows
ENV HOME /home/ows

ADD gitclone.sh /home/ows/$GITCLONE
RUN cd /home/ows && ./$GITCLONE
#RUN git config --global http.sslVerify "false"
#RUN git clone https://scm.gforge.inria.fr/anonscm/git/dose/dose.git 
#RUN git clone https://github.com/OCaml/opam.git 
#RUN git clone https://github.com/OCamlPro/ows.git 

RUN cd /home/ows/opam && ./configure && make lib-ext all
RUN cd /home/ows/dose && ./configure && make

ADD ows.conf /home/ows/ows
RUN cd /home/ows/ows && DEFAULTS=/home/ows/ows/ows.conf ./ows-update -s
RUN ls -la /home/ows/repository
RUN cd /home/ows/ows && DEFAULTS=/ows.conf scripts/ows-cron replay 10
EOF

docker build -t ows-devel --no-cache . 
