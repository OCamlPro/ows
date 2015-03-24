
## OWS Opam Weather Service

A service to analyse the state of the opam repository w.r.t.
all available version of the OCaml compiler.

## Dependencies
- CSS
 * bootstrap ( http://getbootstrap.com/css/ )
 * weather-icons ( https://github.com/erikflowers/weather-icons )
 * datatables ( https://datatables.net )
- JS
 * jquery ( https://jquery.com/ )

## How To Use ?

''ows-update'' initializes a local opam repository and keeps it up-to-date.
It can be run from a cron script. It creates a directory where it stores
all the opam universes and the result of distcheck and initialize the html
root directory. Ex :

    ows-update 2015-03-12 2015-03-13

''ows.py'' takes a local directory containing the distcheck results and
aggregates and build one ows report. Usually ows.py is run in a for cycle :

    for i in reports/2015-03-2*/* ; do 
      ./ows.py --baseurl "http://ows.irill.org" $i; 
    done

''ows-archive'' takes care of archiving all html reports older then 10 days.
it can be run from a cron script. Ex :

    ./ows-archive html 11
