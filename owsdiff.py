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
import os, signal, sys
import argparse
import datetime as dt
import time
import shutil

from subprocess import Popen, PIPE, STDOUT
from itertools import groupby, izip_longest
from operator import itemgetter, attrgetter, methodcaller

from collections import defaultdict
from collections import OrderedDict

import tempfile

datefmt = "%a %b %d %H:%M:%S %Z %Y"

import pprint
pp = pprint.PrettyPrinter(indent=4)

import os, pwd
os.getlogin = lambda: pwd.getpwuid(os.getuid())[0]

import git, os, shutil
from git.exc import GitCommandError

# Ocaml Releases (add here a new one)
VERSIONS="3.12.1 4.00.1 4.01.0 4.02.0 4.02.1"
DISTCHECK="/home/ows/dose/distcheck.native"
OPAM="/home/ows/opam/src/opam"
OPAMREPO="/srv/data/ows/repository/opam-repository"
OPAMROOT="/srv/data/ows/repository/opam-root"
OWSCACHE="/srv/data/ows/cache"

def runopam(switches,reportdir,nocache=False):
    if not os.path.exists(reportdir) :
        os.makedirs(reportdir)

    if not os.path.exists(reportdir) :
        FNULL = open(os.devnull, 'w')
        print "Update Opam"
        cmd = [OPAM,'update','--quiet','--use-internal-solver']
        proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env={'OPAMROOT' : OPAMROOT})
        proc.communicate()
    else :
        print "Skip Opam update. Using cache"

    for switch in switches :
        print "Switch %s" % switch

        outfile=os.path.join(reportdir,"report-%s.pef"  % switch)
        if not os.path.exists(outfile) :
            print "Saving pef in %s" % outfile
            cmd = [OPAM,'config','pef-universe','--quiet','--use-internal-solver','--switch',switch]

            with open(outfile,'w') as f :
                proc = Popen(cmd,stdout=f,env={'OPAMROOT' : OPAMROOT})
                proc.communicate()
                f.close()
        else :
            print "Using Cache report-%s.pef"  % switch

        inputfile = outfile
        outfile=os.path.join(reportdir,"report-%s.yaml" % switch)
        if not os.path.exists(outfile) :
            print "Running Distcheck %s" % outfile
            cmd = [DISTCHECK,'-f','-s','-tpef', inputfile]
            with open(outfile,'wa+') as f :
                f.write("ocaml_switch: %s\n" % switch)
                f.flush()

                proc = Popen(cmd,stdout=f)
                proc.communicate()
                f.close()
        else :
            print "Using Cache report-%s.yaml"  % switch

def replay(commit) : 
    print "Fetch Commit %s" % commit
    repo = git.Repo(OPAMREPO)
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.git.checkout(commit)

def parse(f):
    data = yaml.load(f, Loader=yamlLoader)
    d = {}
    if 'broken-packages' in data : 
        data = { x.replace('-', '_'): data[x] for x in data.keys() }
        d['broken_packages'] = int(data['broken_packages'])
        d['total_packages'] = int(data['total_packages'])
        d['switch'] = data['ocaml_switch']
        d['report'] = {}
        for name, group in groupby(data['report'], lambda x: x['package']):
            for p in group:
                d['report'].setdefault(name,[p]).append(p)
    return d

def makeset(r):
    ok = set()
    broken = set()
    for n,v in r['report'].iteritems() :
        for p in v :
            if p['status'] == 'ok' : 
                ok.add((n,p['version']))
            elif p['status'] == 'broken' :
                broken.add((n,p['version']))

    return (ok,broken)

def load_and_parse(reportdir,commit1,commit2,nocache=False):
    def get(path) :
        report = []
        for root, dirs, files in os.walk(path, topdown=False):
            for name in fnmatch.filter(files, "*.yaml"):
                fname = os.path.join(root, name)
                print "Parse ", fname
                with open(fname) as dataset :
                    r = parse(dataset)
                    if r :
                        report.append(r)
                    dataset.close()
        return report

    def run(reportdir, nocache=False) :
        picklefile = os.path.join(reportdir,'data.pickle')
        print picklefile
        if not os.path.exists(reportdir) :
            os.makedirs(reportdir)
#        if nocache and os.path.exists(picklefile) :
#            os.remove(picklefile)

        if os.path.exists(picklefile) :
            print "Load Cache %s" % picklefile
            with open(picklefile,'r') as f :
                ro = pickle.load(f)
        else :
            ro = sorted(get(reportdir),key=lambda r: r['switch'])
            s = signal.signal(signal.SIGINT, signal.SIG_IGN)
            with open(picklefile,'wb') as f :
                pickle.dump(ro,f)
                f.close()
            signal.signal(signal.SIGINT, s)
        return ro

    ro1 = run(os.path.join(reportdir,commit1))
    ro2 = run(os.path.join(reportdir,commit2))

    return (zip(ro1,ro2))

def printset(commit,d) :
    for (new,rem,fixed,broken,switch) in d :
        print "Switch: %s" % switch
        if len(new) > 0 :
            print "These packages are NEW (%s)" % commit
            for (n,v) in new :
                print "(%s,%s)" % (n,v)

        if len(rem) > 0 :
            print "These packages were REMOVED (%s)" % commit
            for (n,v) in rem :
                print "(%s,%s)" % (n,v)

        if len(fixed) > 0 :
            print "These packages were FIXED (%s)" % commit
            for (n,v) in fixed :
                print "(%s,%s)" % (n,v)

        if len(broken) :
            print "These packages are now BROKEN (%s)" % commit
            for (n,v) in broken :
                print "(%s,%s)" % (n,v)

    print
 

def compare(reportdir,commit1,commit2) :
    print "Comparing reports %s - %s" % (commit1,commit2)
    d = []
    for (r1,r2) in load_and_parse(reportdir,commit1,commit2) :
        (ok1,br1) = makeset(r1)
        (ok2,br2) = makeset(r2)
        switch = r1['switch']
        
        new = list(((ok2 | br2) - (ok1 | br1)))
        rem = list(((ok1 | br1) - (ok2 | br2)))
        fixed = [p for p in br1 if p in ok2]
        broken = [p for p in br2 if p in ok1]

        d.append({ 
            'new' : new, 
            'rem' : rem, 
            'fixed' : fixed, 
            'broken' : broken, 
            'switch' : r1['switch']
        })

    return d

def run(commit1,commit2) :

    reportdir = tempfile.mkdtemp('ows-diff')
    reportdir = OWSCACHE
    switches=VERSIONS.split()

    replay(commit1)
    runopam(switches,os.path.join(reportdir,commit1))

    replay(commit2)
    runopam(switches,os.path.join(reportdir,commit2))

    d = compare(reportdir,commit1,commit2)
    return d

def patch(commit,patchfile):
    newbranch="ows-travis-branch"
    author=git.Actor("ows", "ows@irill.org")

    repo = git.Repo(OPAMREPO)
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.remotes.origin.fetch()
    repo.git.checkout('master')
    try :
        repo.git.branch('-D',newbranch)
    except GitCommandError :
        pass

    repo.git.checkout(commit,b=newbranch)
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.git.apply(patchfile)
    repo.index.commit("travis")

    diff = run(commit,str(repo.commit()))

    d = os.path.join(OWSCACHE,str(repo.commit()))
    if os.path.exists(d) :
        shutil.rmtree(d)

    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.git.checkout('master')
    repo.git.branch('-D',newbranch)

    return diff

def main():
    parser = argparse.ArgumentParser(description='Confront two distcheck reports')
    parser.add_argument('commit1', nargs=1, help="reference commit (git ref)")
    parser.add_argument('commit2', nargs=1, help="new commit (git ref)")
    args = parser.parse_args()

    commit1 = args.commit1[0]
    commit2 = args.commit2[0]
    d = run(commit1,commit2)
    printset(commit1,d)

if __name__ == '__main__':
    main()
