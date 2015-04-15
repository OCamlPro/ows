
## OWS Opam Weather Service

A service to analyse the state of the opam repository w.r.t.
all available version of the OCaml compiler.

OWS is distributed under the GNU AGPLv3 licence.
 
Copyright : 2015 Inria
 
Author(s) : Pietro Abate <pietro . abate @ pps . univ - paris - diderot . fr>


## Dependencies
- CSS
 * bootstrap ( http://getbootstrap.com/css/ )
 * weather-icons ( https://github.com/erikflowers/weather-icons )
 * datatables ( https://datatables.net )
- JS
 * jquery ( https://jquery.com/ )
 * query svg plugin ( http://keith-wood.name/svg.html )
- Python
 * python-pydot
 * python-yaml
 * python-matplotlib
 * python-jinja2

## Setup

  Modify all relevant variables in ''ows-update'' to match your environment
  
  BASEDIR=~/Projects/repos/ows
  VERSIONS=${VERSIONS:-"3.12.1 4.00.1 4.01.0 4.02.0 4.02.1"}
  DISTCHECK=~/Projects/repos/mancoosi-tools/dose/dose-distcheck
  OPAM=~/Projects/repos/opam/src/opam
  REPORTDIR=${BASEDIR}/reports
  DATADIR=${BASEDIR}/repository
  TMPDIR=/tmp

  run ''ows-update -s'' to checkout the opam repository and configure it for ows

  copy the directories ''css fonts images js'' to the target html directory

## How To Use ?

''ows-update'' initializes a local opam repository and keeps it up-to-date.
It can be run from a cron script. It creates a directory where it stores
all the opam universes and the result of distcheck and initialize the html
root directory. Ex :

    ows-update 2015-03-12 2015-03-13

''ows-run'' takes a local directory containing the distcheck results and
aggregates and build one ows report. Usually ows.py is run in a for cycle :

    for i in reports/2015-03-2*/* ; do 
      ./ows-run --baseurl "http://ows.irill.org" $i; 
    done

''ows-archive'' takes care of archiving all html reports older then 10 days.
it can be run from a cron script. Ex :

    ./ows-archive html 11

