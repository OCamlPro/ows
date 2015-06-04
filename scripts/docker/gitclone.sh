#!/bin/bash
git config --global http.sslVerify "false"

if [ ! -d dose ]; then
  git clone https://scm.gforge.inria.fr/anonscm/git/dose/dose.git 
else
  cd dose && git pull
fi

if [ ! -d opam ]; then
  git clone https://github.com/OCaml/opam.git
else
  cd opam && git pull
fi

if [ ! -d ows ]; then
  git clone https://github.com/OCamlPro/ows.git
else
  cd ows && git pull
fi
