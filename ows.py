#!/usr/bin/python

import yaml
try :
    from yaml import CBaseLoader as yamlLoader
except ImportError:
    from yaml import BaseLoader as yamlLoader
    warning('YAML C-library not available, falling back to python')

try :
    import cPickle as pickle
except ImportError:
    import pickle
    warning('Pickle C-library not available, falling back to python')

import fnmatch
import os
import argparse
import csv
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib import dates
import os.path
from itertools import groupby, izip_longest
from operator import itemgetter, attrgetter, methodcaller
import collections
from collections import defaultdict
from collections import OrderedDict

from jinja2 import Environment, FileSystemLoader

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
datefmt = "%a %b %d %H:%M:%S %Z %Y"

def parse(f):
    data = yaml.load(f, Loader=yamlLoader)
    d = {}
    if 'broken-packages' in data : 
        data = { x.replace('-', '_'): data[x] for x in data.keys() }
        d['broken_packages'] = data['broken_packages']
        d['total_packages'] = data['total_packages']
        d['ocaml_switch'] = data['ocaml_switch']
        d['date'] = data['git_date']
        d['commit'] = data['git_commit']
        d['title'] = data['git_title']
        d['author'] = data['git_author']
        d['summary'] = data['summary']
        d['report'] = {}
        for name, group in groupby(data['report'], lambda x: x['package']):
            for p in group:
                #print "%s => %s." % (name, p)
                if name in d['report'] :
                    d['report'][name].append(p)
                else :
                    d['report'][name] = [p]

    return d

#    { pippo : [ { 1.1 : { 4.01 : ok, 4.02 : broken } }, { 1.2 : { 4.01 : ok, 4.02 : broken } }, ] }
def aggregate(d):
    aggregatereport = {}
    aggregatesummary = { 'conflict' : {} , 'missing' : {} }
    summary = {}
    date = None
    title = None
    author = None
    commit = None
    for report in d :
        if report :
            date = report['date']
            title = report['title']
            author = report['author']
            commit = report['commit']
            switch = report['ocaml_switch']
            for a in report['summary'] :
                if 'missing' in a :
                    breaks = int(a['missing']['breaks'])
                    pkg = (a['missing']['pkg']['package'],a['missing']['pkg']['version'])
                    s = { 'breaks' : breaks , 'packages' : a['missing']['packages'] }
                    if pkg in aggregatesummary['missing']:
                        aggregatesummary['missing'][pkg][switch] = s
                    else :
                        aggregatesummary['missing'][pkg] = { switch :  s }
                    if 'total' in aggregatesummary['missing'][pkg] :
                        aggregatesummary['missing'][pkg]['total'] += breaks
                    else :
                        aggregatesummary['missing'][pkg]['total'] = breaks

                elif 'conflict' in a :
                    pkg1 = (a['conflict']['pkg1']['package'],a['conflict']['pkg1']['version'])
                    pkg2 = (a['conflict']['pkg2']['package'],a['conflict']['pkg2']['version'])
                    breaks = int(a['conflict']['breaks'])
                    s = { 'breaks' : breaks , 'packages' : a['conflict']['packages'] }
                    if (pkg1,pkg2) in aggregatesummary['conflict'] :
                        aggregatesummary['conflict'][(pkg1,pkg2)][switch] = s
                    else :
                        aggregatesummary['conflict'][(pkg1,pkg2)] = { switch : s }
                    if 'total' in aggregatesummary['conflict'][(pkg1,pkg2)] :
                        aggregatesummary['conflict'][(pkg1,pkg2)]['total'] += breaks
                    else :
                        aggregatesummary['conflict'][(pkg1,pkg2)]['total'] = breaks

            for name, l in report['report'].iteritems() :
                if name not in aggregatereport :
                    aggregatereport[name] = {}
                    summary[name] = {}

                status = {'ok' : 0, 'broken' : 0}
                for s,group in groupby(l, lambda p: p['status']) :
                    status[s] = len(list(group))

                if status['ok'] == len(l) :
                    summary[name][switch] = "ok"
                elif status['broken'] == len(l) :
                    summary[name][switch] = "broken"
                else :
                    summary[name][switch] = "partial"

                for package in l :
                    ver = package['version']
                    r = package['reasons'] if package['status'] == "broken" else None
                    direct = False
                    indirect = False
                    dc,dm = [],[] # direct conflicts, direct missing
                    idc,idm = [], {} # indirect conflicts, indirect missing
                    if 'reasons' in package :
                        for p in package['reasons'] :
                            if 'missing' in p :
                                pkgname = p['missing']['pkg']['package']
                                pkgvers = p['missing']['pkg']['version']
                                unsatdep = p['missing']['pkg']['unsat-dependency']
                                if pkgname == name :
                                    direct = True
                                    dm.append(unsatdep)
                                else :
                                    indirect = True
                                    if pkgname not in idm :
                                        idm[pkgname] = [pkgvers]
                                    else :
                                        idm[pkgname].append(pkgvers)

                            if 'conflict' in p :
                                p1 = p['conflict']['pkg1']['package']
                                p2 = p['conflict']['pkg2']['package']
                                v1 = p['conflict']['pkg1']['version']
                                v2 = p['conflict']['pkg2']['version']
                                if p['conflict']['pkg1']['package'] == name or p['conflict']['pkg2']['package'] == name :
                                    direct = True
                                    dc.append(((p1,v1),(p2,v2)))
                                else :
                                    indirect = True
                                    idc.append(((p1,v1),(p2,v2)))

                    p = (package['status'],(direct,indirect),dc,dm,idc,idm,r)
                    if ver in aggregatereport[name] :
                        aggregatereport[name][ver][switch] = p
                    else :
                        aggregatereport[name][ver] = { switch : p }

    summaryreport = {}
    summaryreport['totalnames'] = len(aggregatereport)
    summaryreport['broken'] = 0
    summaryreport['partial'] = 0
    summaryreport['correct'] = 0
    summaryreport['report'] = summary
    summaryreport['date'] = dt.datetime.strptime(date,datefmt)
    summaryreport['title'] = title
    summaryreport['author'] = author
    summaryreport['commit'] = commit
    summaryreport['summary'] = aggregatesummary

    switchnumber = len(d)
    for name,switches in summary.iteritems() :
        broken,correct,undefined,total_versions = 0,0,0,0
        for version, results in aggregatereport[name].iteritems() :
            for s in switches :
                total_versions += 1
                if s in results :
                    if results[s][0] == "broken" :
                        broken += 1
                    else :
                        correct += 1
                else :
                    undefined += 1
        summaryreport['report'][name]['percent'] = int(100.0 * (float(broken) / float(total_versions)))
        if broken == total_versions - undefined :
            summaryreport['broken'] += 1
            summaryreport['report'][name]['status'] = "broken"
        elif correct == total_versions - undefined :
            summaryreport['correct'] += 1
            summaryreport['report'][name]['status'] = "ok"
        else :
            summaryreport['partial'] += 1
            summaryreport['report'][name]['status'] = "partial"

    summaryreport['report'] = OrderedDict(sorted(summaryreport['report'].items(), key=lambda x : x[1]['percent'],reverse=True))
    summaryreport['summary']['missing'] = OrderedDict(sorted(summaryreport['summary']['missing'].items(), key=lambda x: x[1]['total'],reverse=True))
    summaryreport['summary']['conflict'] = OrderedDict(sorted(summaryreport['summary']['conflict'].items(), key=lambda x: x[1]['total'],reverse=True))

    return aggregatereport,summaryreport

def html_backlog(history,summaryreport):
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
    shortdate = summaryreport['date'].strftime("%Y-%m-%d")
    template = j2_env.get_template('templates/backlog.html')
    output = template.render({'history': history, 'summary' : summaryreport})
    dirname = os.path.join("html",shortdate)
    if not os.path.exists(dirname) :
        os.makedirs(dirname)
    fname = os.path.join(dirname,"backlog.html")
    with open(fname, 'w') as f:
        f.write(output)
 
def html_weather(aggregatereport,summaryreport,switches):
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
    shortdate = summaryreport['date'].strftime("%Y-%m-%d")
    for name,versions in aggregatereport.iteritems() :
        template = j2_env.get_template('templates/package.html')
        output = template.render({'name' : name, 'versions' : versions, 'switches': switches, 'date' : summaryreport['date']})
        dirname = os.path.join("html",shortdate,'packages')
        if not os.path.exists(dirname) :
            os.makedirs(dirname)
        fname = os.path.join(dirname,name+".html")
        #print "Saving ",fname
        with open(fname, 'w') as f:
            f.write(output)
    template = j2_env.get_template('templates/weather.html')
    output = template.render({'summary' : summaryreport, 'switches': switches})
    dirname = os.path.join("html",shortdate)
    if not os.path.exists(dirname) :
        os.makedirs(dirname)
    fname = os.path.join(dirname,"weather.html")
    with open(fname, 'w') as f:
        f.write(output)
 
def html_summary(summaryreport,switches):
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
    shortdate = summaryreport['date'].strftime("%Y-%m-%d")
    for t,s in summaryreport['summary'].iteritems() :
        if t == 'missing' :
            for (name,version),a in s.iteritems() :
                rows = []
                for sw,b in a.iteritems() :
                    l = []
                    if sw != 'total' :
                        for n,group in groupby(b['packages'], lambda p: p['package']) :
                            ll = map(lambda p: p['version'],list(group))
                            l.append((n,ll))
                        rows.append([sw] + l)
                rows = map(lambda x: list(x),izip_longest(*(sorted(rows,key=lambda x : x[0]))))
                template = j2_env.get_template('templates/packagelist.html')
                title = "%s %s (ows : %s)" % (name,version,summaryreport['date'])
                output = template.render({'title' : title, 'summary' : rows, 'switches': switches})
                dirname = os.path.join("html",shortdate,'summary')
                if not os.path.exists(dirname) :
                    os.makedirs(dirname)
                fname = os.path.join(dirname,name+version+".html")
                #print "Saving ",fname
                with open(fname, 'w') as f:
                    f.write(output)
        if t == 'conflict' :
            for (pkg1,pkg2),a in s.iteritems() :
                rows = []
                for sw,b in a.iteritems() :
                    l = []
                    if sw != 'total' :
                        for n,group in groupby(b['packages'], lambda p: p['package']) :
                            ll = map(lambda p: p['version'],list(group))
                            l.append((n,ll))
                        rows.append([sw] + l)
                rows = map(lambda x: list(x),izip_longest(*(sorted(rows,key=lambda x : x[0]))))
                template = j2_env.get_template('templates/packagelist.html')
                title = "%s %s # %s %s (ows : %s)" % (pkg1[0],pkg1[1],pkg2[0],pkg2[1],summaryreport['date'])
                output = template.render({'title': title, 'summary' : rows, 'switches': switches})
                dirname = os.path.join("html",shortdate,'summary')
                if not os.path.exists(dirname) :
                    os.makedirs(dirname)
                fname = os.path.join(dirname,pkg1[0]+pkg1[1]+"-"+pkg2[0]+pkg2[1]+".html")
                #print "Saving ",fname
                with open(fname, 'w') as f:
                    f.write(output)

    template = j2_env.get_template('templates/summary.html')
    output = template.render({'summary' : summaryreport, 'switches': switches})
    dirname = os.path.join("html",shortdate)
    if not os.path.exists(dirname) :
        os.makedirs(dirname)
    fname = os.path.join(dirname,"summary.html")
    with open(fname, 'w') as f:
        f.write(output)
 
def main():
    parser = argparse.ArgumentParser(description='create ows static pages')
    parser.add_argument('-v', '--verbose')
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    parser.add_argument('--nocache', action='store_true', default=False)
    parser.add_argument('reportdir', type=str, nargs=1, help="dataset")
    args = parser.parse_args()

    reportdir = args.reportdir[0]
    picklefile = os.path.join(reportdir,'data.pickle')

    if args.nocache and os.path.exists(picklefile) :
        os.remove(picklefile)

    if os.path.exists(picklefile) :
        print ("Skip parsing ", picklefile)
        (switches,ar,sr) = pickle.load(open(picklefile,'r'))
    else :
        report = []
        switches = []
        for root, dirs, files in os.walk(reportdir, topdown=False):
            for name in fnmatch.filter(files, "*.yaml"):
                fname = os.path.join(root, name)
                print ("Parse ", fname)
                dataset = open(fname)
                r = parse(dataset)
                if r : 
                    switches.append(r['ocaml_switch'])
                    report.append(r)
                dataset.close()

        print ("Aggregate ", picklefile)
        (ar,sr) = aggregate(report)
        f = open(picklefile,'wb')
        pickle.dump((switches,ar,sr),f)
        f.close()

    historydir = "reports"
    picklehist = os.path.join(historydir,'history.pickle')

    print ("Load History ",sr['date'])
    h = {}
    if os.path.exists(picklehist) :
        f = open(picklehist,'r')
        h = pickle.load(f)
        f.close()

    h[sr['date']] = {}
    h = OrderedDict(sorted(h.items(),key=lambda r: r[0]))

    weather = {}
    history = list(h.items())
    # we assume the monotonicity of the opam repo
    for p,v in sr['report'].iteritems() :
        if v['percent'] == 0 :
            weather_today = "sunny"
        elif v['percent'] < 0 and v['percent'] >= 20 :
            weather_today = "cloudy"
        else :
            weather_today = "stormy"
        if len(history) > 1 :
            today = h.keys().index(sr['date'])
            yesterday = today - 1
            if p in history[yesterday][1]['summary']['weather'] : 
                weather_yesterday = list(history[yesterday][1]['summary']['weather'][p])[-1]
                if weather_yesterday == weather_today :
                    weather[p] = [weather_today]
                else :
                    weather[p] = [ weather_yesterday, weather_today ]
            else :
                weather[p] = [weather_today]
        else :
            weather[p] = [weather_today]
    sr['weather'] = weather

    print ("Weather")
    html_weather(ar,sr,switches)
    print ("Summary")
    html_summary(sr,switches)
    print ("Done")

    print ("Save History ",sr['date'])
    del sr['report']
    del sr['summary']
    newsummary = { 'switches' : switches , 'summary' : sr }
    h[sr['date']] = newsummary

    print "BackLog"
    html_backlog(h,sr)

    f = open(picklehist,'wb')
    pickle.dump(h,f)
    f.close()

if __name__ == '__main__':
    main()
