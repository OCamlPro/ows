#!/usr/bin/python

import yaml
try :
    from yaml import CBaseLoader as yamlLoader
except ImportError:
    from yaml import BaseLoader as yamlLoader
    warning('YAML C-library not available, falling back to python')

import os.path
from codecs import open
import fnmatch
import os, signal, sys
import argparse
import datetime as dt
import time

from subprocess import Popen, PIPE, STDOUT
from itertools import groupby, izip_longest
from operator import itemgetter, attrgetter, methodcaller

from collections import defaultdict
from collections import OrderedDict

import tempfile

datefmt = "%a %b %d %H:%M:%S %Z %Y"

import pprint
pp = pprint.PrettyPrinter(indent=4)

import git, os, shutil

# Ocaml Releases (add here a new one)
VERSIONS="3.12.1 4.00.1 4.01.0 4.02.0 4.02.1"
DISTCHECK="/home/abate/Projects/repos/mancoosi-tools/dose/dose-distcheck"
OPAM="/home/abate/Projects/repos/opam/src/opam"
OPAMREPO="/home/abate/Projects/repos/ows/repository/opam-repository"
OPAMROOT="/home/abate/Projects/repos/ows/repository/opam-root"

def runopam(switches,reportdir):
    if not os.path.exists(reportdir) :
        os.makedirs(reportdir)

    FNULL = open(os.devnull, 'w')
    print "Update Opam"
    cmd = [OPAM,'update','--quiet','--use-internal-solver']
    proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env={'OPAMROOT' : OPAMROOT})
    proc.communicate()

    for switch in switches :
        print "Switch %s" % switch

        outfile=os.path.join(reportdir,"report.pef")
        print "Saving pef in %s" % outfile
        cmd = [OPAM,'config','pef-universe','--quiet','--use-internal-solver','--switch',switch]

        with open(outfile,'w') as f :
            proc = Popen(cmd,stdout=f,env={'OPAMROOT' : OPAMROOT})
            proc.communicate()
            f.close()

        inputfile = outfile
        outfile=os.path.join(reportdir,"report-%s.yaml" % switch)
        print "Running Distcheck %s" % outfile
        cmd = [DISTCHECK,'-f','-s','-tpef', inputfile]
        with open(outfile,'wa+') as f :
            f.write("ocaml_switch: %s\n" % switch)
            f.flush()

            proc = Popen(cmd,stdout=f)
            proc.communicate()
            f.close()

def replay(commit) : 
    print "Fetch Commit %s" % commit
    repo = git.Repo(OPAMREPO)
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
#    repo.remotes.origin.fetch()
    repo.git.checkout(commit)
#    repo.git.reset('--hard',commit)
#    repo.git.clean('-xdf')

    print list(repo.iter_commits())[0]

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

def load_and_parse(reportdir,commit1,commit2):
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
    r1 = get(os.path.join(reportdir,commit1))
    r2 = get(os.path.join(reportdir,commit2))
    ro1 = sorted(r1,key=lambda r: r['switch'])
    ro2 = sorted(r2,key=lambda r: r['switch'])
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

        d.append((new,rem,fixed,broken,r1['switch']))

    pp.pprint(d)

    return d

def run(commit1,commit2) :

    reportdir = tempfile.mkdtemp('ows-diff')
    switches=VERSIONS.split()

    replay(commit1)
    print reportdir
    print commit1
    runopam(switches,os.path.join(reportdir,commit1))

    replay(commit2)
    runopam(switches,os.path.join(reportdir,commit2))

    d = compare(reportdir,commit1,commit2)
    return d

def patch(commit,patchfile):
    newbranch=str(uuid.uuid1())

    repo = git.Repo(owsdiff.OPAMREPO)
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
#    repo.remotes.origin.fetch()

    repo.git.checkout(commit,b=newbranch)
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.git.apply(patchfile)
    repo.index.commit("travis")

    diff = owsdiff.run(commit,str(repo.commit()))

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
