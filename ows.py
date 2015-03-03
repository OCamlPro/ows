#!/usr/bin/python

import yaml
import os
import argparse
import csv
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib import dates
import os.path
from itertools import groupby
from operator import itemgetter, attrgetter, methodcaller
import collections
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

def parse(f):
    data = yaml.load(f)
    d = {}
    if 'broken-packages' in data : 
        data = { x.replace('-', '_'): data[x] for x in data.keys() }
        d['broken_packages'] = data['broken_packages']
        d['total_packages'] = data['total_packages']
        d['ocaml_switch'] = data['ocaml_switch']
        d['date'] = data['date']
        d['report'] = {}
        for name, group in groupby(data['report'], lambda x: x['package']):
            for p in group:
              #  print "%s => %s." % (name, p)
                if name in d['report'] :
                    d['report'][name].append(p)
                else :
                    d['report'][name] = [p]
    return d

#    { pippo : [ { 1.1 : { 4.01 : ok, 4.02 : broken } }, { 1.2 : { 4.01 : ok, 4.02 : broken } }, ] }
def aggregate(d):
    aggregatereport = {}
    summaryreport = {}
    for report in d :
        if report :
            date = report['date']
            switch = report['ocaml_switch']
            for name, l in report['report'].iteritems() :
                if name not in aggregatereport :
                    aggregatereport[name] = {}
                    summaryreport[name] = {}

                status = {'ok' : 0, 'broken' : 0}
                for s,group in groupby(l, lambda p: p['status']) :
                    status[s] = len(list(group))

                if status['ok'] == len(l) :
                    summaryreport[name][switch] = "ok"
                elif status['broken'] == len(l) :
                    summaryreport[name][switch] = "broken"
                else :
                    summaryreport[name][switch] = "partial"

                for package in l :
                    ver = package['version']
                    s = {switch:package['status']}
                    if ver in aggregatereport[name] :
                        aggregatereport[name][ver][switch] = package['status']
                    else :
                        aggregatereport[name][ver] = s

    return date,aggregatereport,summaryreport

# total number of package names on all Switch
# total number of packages for each Switch

# a package is Broken if it is broken for All (declared) Switch
# a package is Partially Broken if it is broken on Some (declared) Switch
# a package is Correct if it is installable on All (declared) Switch

def html_package(aggregatereport,switches,date):
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
    for name,versions in aggregatereport.iteritems() :
        template = j2_env.get_template('templates/package.html')
        output = template.render({'name' : name, 'versions' : versions, 'switches': switches})
        dirname = os.path.join("html",str(date),'packages')
        if not os.path.exists(dirname) :
            os.makedirs(dirname)
        fname = os.path.join(dirname,name+".html")
        with open(fname, 'w') as f:
            f.write(output)

def html_summary(aggregatereport,summaryreport,switches,date):
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
    template = j2_env.get_template('templates/summary.html')
    output = template.render({'report' : aggregatereport, 'summary' : summaryreport, 'switches': switches})
    dirname = os.path.join("html",str(date))
    if not os.path.exists(dirname) :
        os.makedirs(dirname)
    fname = os.path.join(dirname,"summary.html")
    with open(fname, 'w') as f:
        f.write(output)
 
def html_weather(report):
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
    template = j2_env.get_template('templates/report.html')
    output = template.render(report)
    dirname = os.path.join("html",str(report['date']))
    if not os.path.exists(dirname) :
        os.makedirs(dirname)
    fname = os.path.join(dirname,"report-"+report['ocaml_switch']+".html")
    with open(fname, 'w') as f:
        f.write(output)
 
def main():
    parser = argparse.ArgumentParser(description='create ows static pages')
    parser.add_argument('-v', '--verbose')
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    parser.add_argument('--releases', type=str, nargs=1, help="release timeline")
    parser.add_argument('reportdir', type=str, nargs=1, help="dataset")
    args = parser.parse_args()

    report = []
    switches = []
    for root, dirs, files in os.walk(args.reportdir[0], topdown=False):
        for name in files:
            fname = os.path.join(root, name)
            #print(fname)
            dataset = open(fname)
            r = parse(dataset)
            if r : 
                html_weather(r)
                switches.append(r['ocaml_switch'])
                report.append(r)
            dataset.close()

    date,ar,sr = aggregate(report)
    html_package(ar,switches,date)
    html_summary(ar,sr,switches,date)

if __name__ == '__main__':
    main()
