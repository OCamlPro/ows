#!/bin/bash

cat <<EOF > ows.conf
BASEDIR=/repos/ows
VERSIONS="${VERSIONS:-"4.02.1 4.01.0 4.02.0 4.00.1 3.12.1"}"

DISTCHECK=/dose/distcheck.native

OPAM=/opam/src/opam
OPAMOPTIONS="--use-internal-solver"

OWSRUN=/ows/ows-run
OWSARCHIVE=/ows/ows-archive
OWSUPDATE=/ows/ows-update

REPORTDIR=${BASEDIR}/reports

DATADIR=${BASEDIR}/repository

TMPDIR=/tmp

TARGETDIR=${BASEDIR}/html

BASEURL=http://localhost:8000
EOF

GITCLONE=$RANDOM-gitclone.sh
cat <<EOF > Dockerfile
FROM debian:jessie
MAINTAINER Pietro Abate <pietro.abate@pps.univ-paris-diderot.fr>

RUN echo "deb http://ftp.fr.debian.org/debian unstable main" > /etc/apt/sources.list
RUN apt-get update

RUN apt-get install --no-install-recommends --yes \
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

ADD gitclone.sh /$GITCLONE
RUN ./$GITCLONE
#RUN git config --global http.sslVerify "false"
#RUN git clone https://scm.gforge.inria.fr/anonscm/git/dose/dose.git 
#RUN git clone https://github.com/OCaml/opam.git 
#RUN git clone https://github.com/OCamlPro/ows.git 

RUN cd opam && ./configure && make lib-ext all
RUN cd dose && ./configure && make

ADD ows.conf /
RUN cd ows && DEFAULTS=/ows.conf ./ows-update -s
RUN ls -la /repository
RUN cd ows && DEFAULTS=/ows.conf scripts/ows-cron replay 10
EOF

docker build .
