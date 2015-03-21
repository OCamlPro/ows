#!/bin/bash

#set -x

#################### Config Variables ########################
BASEDIR=~/Projects/repos/ows
VERSIONS=${VERSIONS:-"3.12.1 4.00.1 4.01.0 4.02.0 4.02.1"}
DISTCHECK=~/Projects/repos/mancoosi-tools/dose/dose-distcheck
OPAM=~/Projects/repos/opam/src/opam
REPORTDIR=${BASEDIR}/reports
DATADIR=${BASEDIR}/repository
TMPDIR=/tmp

######################################################################

OPAMROOT=${DATADIR}/opam-root
OPAMREPO=${DATADIR}/opam-repository
OPAMCOMP=${DATADIR}/opam-compilers

export OPAMROOT
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

  local date=$(date --date "$1")
  local commit=$2
  local author=$3
  local title=$4

  for version in ${VERSIONS}; do
    ${OPAM} config cudf-universe --switch ${version} > ${TMPDIR}/report-${version}.pef
    if [ -s ${TMPDIR}/report-${version}.pef ] ; then
      local dirname=${REPORTDIR}/$(date --date "$date" +%Y-"%m-%d")/${commit}/
      mkdir -p ${dirname}
      echo "ocaml-switch: ${version}" > ${dirname}/report-${version}.yaml
      echo "git-date: ${date}" >> ${dirname}/report-${version}.yaml
      echo "git-commit: ${commit}" >> ${dirname}/report-${version}.yaml
      echo "git-author: \"${author}\"" >> ${dirname}/report-${version}.yaml
      #title=$(echo ${title} | sed 's/"/\"/g')
      echo "git-title: |" >> ${dirname}/report-${version}.yaml
      echo " ${title}" >> ${dirname}/report-${version}.yaml
      ${DISTCHECK} pef://${TMPDIR}/report-${version}.pef -m --summary -e -s -f >> ${dirname}/report-${version}.yaml
      mv ${TMPDIR}/report-${version}.pef ${dirname}/
  #    gzip ${REPORTDIR}/${date}/report-${version}.yaml
  #    gzip ${REPORTDIR}/${date}/report-${version}.pef
    fi
  done

}

######################################################################

function rewind_git {
  local commits=""
  local oneday=$(date --date "$1 +1 day")
  if [ ! -z "$1" ]; then
    commits=$(git rev-list -n 1 --since="$1" --until="$oneday" origin/master)
  else
    commits=$(git rev-list -n 1 origin/master)
  fi
  echo "${commits}"
}

function replay {
  local origin="2012-05-19"
  if [ ! -z $1 ]; then
    origin=$1
  fi
  local currentdate=`date +%Y-%m-%d`
  if [ ! -z $2 ]; then
    currentdate=$2
  fi

  git --git-dir ${OPAMREPO}/.git fetch

  # Creation of opam-repository
  local range=$(daterange ${origin} ${currentdate})

  for date in $range; do
      local commits=$(rewind_git "$date")
      echo "replay $date"
      for commit in ${commits}; do
        (cd ${OPAMREPO} && \
        git reset ${commit} --hard && \
        git clean -dxf )
        ${OPAM} update --use-internal-solver 
        local date=$(git show -s --format=%ci ${commit})
        local author=$(git show -s --format=%an ${commit})
        local title=$(git show -s --format=%s ${commit})
        distcheck "$date" "$commit" "$author" "$title"
      done
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
  else 
    yes no | ${OPAM} init --comp=${VERSIONS##* } opam_compilers ${OPAMCOMP}
    ${OPAM} remote add --use-internal-solver -p 0 opam_repository ${OPAMREPO}

    ## Small hack for opam to prefers the "faked' compilers

    ${OPAM} remote remove opam_compilers
    ${OPAM} remote add --use-internal-solver -p 20 opam_compilers ${OPAMCOMP}
    ${OPAM} update --use-internal-solver

    for version in ${VERSIONS}; do
      ${OPAM} switch --use-internal-solver ${version}
    done
  fi
}

function html {
  cp -a js css fonts static/* html/ 
}


#if [ ! -d ${OPAMROOT} ]; then
  setup
#fi

from="2012-05-19"
#from="2012-08-24"
#to="2012-10-19"
#from="2015-02-27"
cd ${OPAMREPO} && replay $from $to
