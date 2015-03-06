#!/bin/bash

#set -x

#################### Config Variables ########################

VERSIONS=${VERSIONS:-"3.12.1 4.00.1 4.01.0 4.02.0 4.02.1"}
DISTCHECK=~/Projects/repos/mancoosi-tools/dose/dose-distcheck
OPAM=~/Projects/repos/opam/src/opam
REPORTDIR=reports
DATADIR=repository
TMPDIR=/tmp

######################################################################

OPAMROOT=${DATADIR}/opam-faked-root
OPAMREPO=${DATADIR}/opam-repository
OPAMCOMP=${DATADIR}/opam-faked-compilers

######################################################################

function daterange {
  local currentdate=$1
  local loopenddate=$(/bin/date --date "$2 1 day" +%Y-%m-%d)

  until [ "$currentdate" == "$loopenddate" ]
  do
    echo $currentdate
    currentdate=$(/bin/date --date "$currentdate 1 day" +%Y-%m-%d)
  done
}

################### Run Distcheck for all declared compilers versions ##########

function distcheck {

  local date=$1
  local commit=$2

  for version in ${VERSIONS}; do
  #echo "mkdir ${REPORTDIR}/${date}"
    mkdir -p ${REPORTDIR}/${date}
    ${OPAM} config cudf-universe --switch ${version} > ${TMPDIR}/report-${version}.pef
    echo "ocaml-switch: ${version}" > ${REPORTDIR}/${date}/report-${version}.yaml
    echo "date: ${date}" >> ${REPORTDIR}/${date}/report-${version}.yaml
    echo "commit: ${commit}" >> ${REPORTDIR}/${date}/report-${version}.yaml
    ${DISTCHECK} pef://${TMPDIR}/report-${version}.pef --summary -e -s -f >> ${REPORTDIR}/${date}/report-${version}.yaml
    mv ${TMPDIR}/report-${version}.pef ${REPORTDIR}/${date}/
#    gzip ${REPORTDIR}/${date}/report-${version}.yaml
#    gzip ${REPORTDIR}/${date}/report-${version}.pef
  done

}

######################################################################

function rewind_git {
  cd ${OPAMREPO}
  local commit=""
  if [ ! -z "$1" ]; then
    commit=$(git rev-list -n 1 --before="$1" origin/master)
  else
    commit=$(git rev-list -n 1 origin/master)
  fi
  git reset ${commit} --hard > /dev/null
  git clean -dxf > /dev/null
  ${OPAM} update --use-internal-solver > /dev/null
  echo "${commit}"
}

function replay {
  local currentdate=`date +%Y-%m-%d`
  local origin="2012-05-19"
  if [ ! -z $1 ]; then
    origin=$1
  fi

  git --git-dir ${OPAMREPO}/.git fetch

  # Creation of opam-repository
  local range=$(daterange ${origin} ${currentdate})

  for date in $range; do

      echo "replay $date"
      local commit=$(rewind_git "$date-12-00-00")
      distcheck $date $commit

  done
}


################### Create a fake opam-repository with 'preinstalled' compilers
function setup {

  for v in ${VERSIONS}; do
    mkdir -p ${OPAMCOMP}/compilers/$v/$v/
    cat > ${OPAMCOMP}/compilers/$v/$v/$v.comp <<EOF
opam-version: "1"
version: "$v"
preinstalled: true
EOF
  done
  echo "0.9.0" > ${OPAMCOMP}/version

  ## Checkout/update the real opam-repository

  if [ ! -d ${OPAMREPO} ]; then
    git clone git://github.com/ocaml/opam-repository ${OPAMREPO}
  else
    ( cd ${OPAMREPO} && \
      git fetch && \
      git reset origin/master --hard && \
      git clean -dxf )
  fi

  ## Initialize OPAM

  if [ -d "${OPAMROOT}" ]; then
    echo "Error: Pre-existent OPAMROOT = ${OPAMROOT}"
    exit 2
  fi

  yes no | ${OPAM} init --comp=${VERSIONS##* } opam_compilers ${OPAMCOMP}
  ${OPAM} remote add --use-internal-solver -p 0 opam_repository ${OPAMREPO}

  ## Small hack for opam to prefers the "faked' compilers

  ${OPAM} remote remove opam_compilers
  ${OPAM} remote add  --use-internal-solver -p 20 opam_compilers ${OPAMCOMP}
  ${OPAM} update --use-internal-solver

  for version in ${VERSIONS}; do
    ${OPAM} switch --use-internal-solver ${version}
  done
}

function html {
  cp js css fonts html
}

origin="2015-02-27"
origin="2012-05-19"
replay $origin
