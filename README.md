
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
 * python-progressbar
- Other
 * optipng (for png compression)
 * hardlink (to hardlink together duplicate files)

#### For ows-wsgi
* python-bottle
* python-git
   
## Setup

Modify all relevant variables in ''ows.config-default'' to match your environment
  
Run ''ows-update -s'' to checkout the opam repository and configure it for ows

Copy the directories ''css fonts images js'' to the target html directory

The directory scripts contains ''ows-cron'' that can be schedule to run at 
regular intervals

## How To Use ?

''ows-update -s'' initializes a local opam repository and initialize the html
root directory.

''ows-update 2015-03-12 2015-03-13''

It creates a directory where it stores all the opam universes and the result of
distcheck and 


''ows-run'' takes a local directory containing the distcheck results and
aggregates and build one ows report. Usually ows.py is run in a for cycle :

    for i in reports/2015-03-2*/* ; do 
      ./ows-run --baseurl "http://ows.irill.org" $i; 
    done

''ows-archive'' takes care of archiving all html reports older then 10 days.
it can be run from a cron script. Ex :

    ./ows-archive html 11

''scripts/ows-cron'' can be run regularly and takes care of keeping the repository
up to date and to generate the ows html pages. It has a number of debugging options.

''ows-wucgi'' is a wucgi server meant to work in conjunction with a web server.
