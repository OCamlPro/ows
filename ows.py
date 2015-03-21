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

import os.path
from codecs import open
import fnmatch
import os, signal
import argparse
import csv
import datetime as dt

import matplotlib.pyplot as plt
from matplotlib import dates
from matplotlib.dates import DateFormatter, date2num

from itertools import groupby, izip_longest
from operator import itemgetter, attrgetter, methodcaller

from collections import defaultdict
from collections import OrderedDict

from jinja2 import Environment, FileSystemLoader

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
j2_env = Environment(loader=FileSystemLoader(THIS_DIR),trim_blocks=True)
datefmt = "%a %b %d %H:%M:%S %Z %Y"

def save_page(output,fname):
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(output)

def parse(f):
    data = yaml.load(f, Loader=yamlLoader)
    d = {}
    if 'broken-packages' in data : 
        data = { x.replace('-', '_'): data[x] for x in data.keys() }
        d['broken_packages'] = int(data['broken_packages'])
        d['total_packages'] = int(data['total_packages'])
        d['switch'] = data['ocaml_switch']
        d['date'] = data['git_date']
        d['commit'] = data['git_commit']
        d['title'] = data['git_title']
        d['author'] = data['git_author']
        d['summary'] = data['summary']
        d['report'] = {}
        for name, group in groupby(data['report'], lambda x: x['package']):
            for p in group:
                if name in d['report'] :
                    d['report'][name].append(p)
                else :
                    d['report'][name] = [p]
    return d

def plot(options,history,switches):
    print "Computing Graph"
    output = os.path.join(options['dirname'],"plot.png")
    fig = plt.figure()
    graph = fig.add_subplot(111)
    h = [x[1]['summary']['totals'] for x in history if 'summary' in x[1]]
    ds = [date2num(x[0]) for x in history if 'summary' in x[1]]
    for s in switches :
        hs = [x[s][2] for x in h]
        graph.plot_date(ds,hs,",-",label=s)

    plt.legend(loc='upper left')
    plt.title('Installable Package versions vs Time')
    fig.autofmt_xdate()
    plt.savefig(output)

def aggregate(d):
    aggregatereport = {}
    aggregatesummary = { 'conflict' : {} , 'missing' : {} }
    summary = {}
    date,title,author,commit,totals = None,None,None,None,{}
    for report in d :
        if report :
            date = report['date']
            title = report['title']
            author = report['author']
            commit = report['commit']
            switch = report['switch']
            totals[switch] = (int(report['total_packages']),int(report['broken_packages']),int(report['total_packages']-report['broken_packages']))
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
    summaryreport['totals'] = totals
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

# we assume the monotonicity of the opam repo
def weather(report, history, today) :
    weather = {}
    yesterday = today - 1
    for p,v in report.iteritems() :
        if v['percent'] == 0 :
            weather_today = "sunny"
        elif v['percent'] < 0 and v['percent'] >= 20 :
            weather_today = "cloudy"
        else :
            weather_today = "stormy"
        if len(history) > 1 :
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
    return weather

def html_backlog(options,history,summaryreport):
    print "Compiling BackLog Page"
    template = j2_env.get_template('templates/backlog.html')
    output = template.render({'history': history, 'summary' : summaryreport, 'baseurl' : options['baseurl']})
    fname = os.path.join(options['dirname'],"backlog.html")
    save_page(output,fname)

def html_about(options,summaryreport):
    print "Compiling About Page"
    template = j2_env.get_template('templates/about.html')
    output = template.render({'summary' : summaryreport, 'baseurl' : options['baseurl']})
    fname = os.path.join(options['dirname'],"about.html")
    save_page(output,fname)
 
def html_weather(options,aggregatereport,summaryreport,switches):
    print "Compiling Weather Page"
    for name,versions in aggregatereport.iteritems() :
        template = j2_env.get_template('templates/package.html')
        output = template.render({'name' : name, 'versions' : versions, 'switches': switches, 'date' : summaryreport['date'], 'baseurl' : options['baseurl']})
        fname = os.path.join(options['dirname'],"packages",name+".html")
        save_page(output,fname)
    template = j2_env.get_template('templates/weather.html')
    output = template.render({'summary' : summaryreport, 'switches': switches, 'baseurl' : options['baseurl']})
    fname = os.path.join(options['dirname'],"index.html")
    save_page(output,fname)
 
def html_summary(options,summaryreport,switches):
    print "Compiling Summary Page"
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
                output = template.render({'title' : title, 'summary' : rows, 'switches': switches, 'baseurl' : options['baseurl']})
                fname = os.path.join(options['dirname'],"summary",name+version+".html")
                save_page(output,fname)
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
                output = template.render({'title': title, 'summary' : rows, 'switches': switches, 'baseurl' : options['baseurl']})
                fname = os.path.join(options['dirname'],"summary",pkg1[0]+pkg1[1]+"-"+pkg2[0]+pkg2[1]+".html")
                save_page(output,fname)

    template = j2_env.get_template('templates/summary.html')
    output = template.render({'summary' : summaryreport, 'switches': switches, 'baseurl' : options['baseurl']})
    fname = os.path.join(options['dirname'],"summary.html")
    save_page(output,fname)

def setup(summaryreport):
    shortdate = summaryreport['date'].strftime("%Y-%m-%d")
    dirname = os.path.join("html",shortdate,summaryreport['commit'])
    if not os.path.exists(dirname) :
        os.makedirs(dirname)
    summary = os.path.join(dirname,'summary')
    if not os.path.exists(summary) :
        os.makedirs(summary)
    packages = os.path.join(dirname,'packages')
    if not os.path.exists(packages) :
        os.makedirs(packages)
    return dirname

def load_or_parse(reportdir,nocache):
    picklefile = os.path.join(reportdir,'data.pickle')

    if nocache and os.path.exists(picklefile) :
        os.remove(picklefile)

    if os.path.exists(picklefile) :
        print "Load Cache"
        (switches,ar,sr) = pickle.load(open(picklefile,'r'))
    else :
        report = []
        switches = []
        for root, dirs, files in os.walk(reportdir, topdown=False):
            for name in fnmatch.filter(files, "*.yaml"):
                fname = os.path.join(root, name)
                print "Parse ", fname
                dataset = open(fname)
                r = parse(dataset)
                if r : 
                    switches.append(r['switch'])
                    report.append(r)
                dataset.close()

        print "Aggregating Data"
        (ar,sr) = aggregate(report)
        s = signal.signal(signal.SIGINT, signal.SIG_IGN)
        f = open(picklefile,'wb')
        pickle.dump((switches,ar,sr),f)
        f.close()
        signal.signal(signal.SIGINT, s)
    return (switches,ar,sr)

def load_history(history,date):
    print "Load History "
    h = {}
    if os.path.exists(history) :
        f = open(history,'r')
        h = pickle.load(f)
        f.close()

    h[date] = {}
    return OrderedDict(sorted(h.items(),key=lambda r: r[0]))

def save_history(history,h,sr,switches):
    print "Saving History "
    del sr['report']
    del sr['summary']
    newsummary = { 'switches' : switches , 'summary' : sr }
    h[sr['date']] = newsummary

    s = signal.signal(signal.SIGINT, signal.SIG_IGN)
    f = open(history,'wb')
    pickle.dump(h,f)
    f.close()
    signal.signal(signal.SIGINT, s)

def main():
    parser = argparse.ArgumentParser(description='create ows static pages')
    parser.add_argument('-v', '--verbose')
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    parser.add_argument('--nocache', action='store_true', default=False)
    parser.add_argument('--baseurl', type=str, nargs=1, help="base url", default="http://localhost:8000/")
    parser.add_argument('--history', type=str, nargs=1, help="history database", default=os.path.join("reports",'history.pickle'))
    parser.add_argument('reportdir', type=str, nargs=1, help="dataset")
    args = parser.parse_args()

    print "Considering ", args.reportdir[0]
    (switches,ar,sr) = load_or_parse(args.reportdir[0],args.nocache)
    options = {'dirname' : setup(sr), 'baseurl' : args.baseurl[0] }

    h = load_history(args.history[0],sr['date'])
    history = list(h.items())
    today = h.keys().index(sr['date'])
    sr['weather'] = weather(sr['report'],history,today)

    html_weather(options,ar,sr,switches)
    html_summary(options,sr,switches)
    html_about(options,sr)
    html_backlog(options,history[today-10:today-1][::-1],sr)
    plot(options,history[:today],switches)

    save_history(args.history[0],h,sr,switches)
    print

if __name__ == '__main__':
    main()
