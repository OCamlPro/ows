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
import os.path
import argparse
import datetime as dt
import time
import shutil
from urlparse import urlparse

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

FNULL = open(os.devnull, 'w')

def initrepo (options) :
    env={'OPAMROOT' : options['opamroot']}
    opamflags = ['--quiet','--use-internal-solver']

    if not os.path.exists(os.path.dirname(options['opamrepo'])):
        print "Initialize ows repository ", os.path.dirname(options['opamrepo'])
        os.makedirs(os.path.dirname(options['opamrepo']),mode=0755)

    for v in options['versions'] :
        dirname = os.path.join(options['opamcomp'],"compilers",v,v)
        if not os.path.exists(dirname) :
            os.makedirs(dirname,mode=0755)

        outfile = os.path.join(options['opamcomp'],"compilers",v,v,"%s.comp" % v)
        with open(outfile,'w') as f :
            f.write('opam-version: "1"')
            f.write('version: "%s"' % v)
            f.write('preinstalled: true')
            f.close()

        outfile = os.path.join(options['opamcomp'],"version")
        with open(outfile,'w') as f :
            f.write("0.9.0")
            f.close()

  ## Checkout/update the real opam-repository

    if not os.path.exists(options['opamrepo']) :
        print "Cloning repo from ", options['giturl']
        git.Repo.clone_from(options['giturl'], options['opamrepo'])
    else :
        repo = git.Repo(options['opamrepo'])
        repo.remotes.origin.fetch()
        repo.git.reset('--hard','origin/master')
        repo.git.clean('-xdf')

  ## Initialize OPAM

    cmd = [options['opam'],'init'] + opamflags + ['--comp=%s' % options['versions'][0],'opam_compilers', options['opamcomp']]
    print ' '.join(cmd)
    proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, stdin=PIPE, env=env)
    proc.stdin.write('no')
    proc.communicate()

    cmd = [options['opam'],'remote'] + opamflags + ['add','-p','0', 'opam_repository', options['opamrepo']]
    print ' '.join(cmd)
    proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env=env)
    proc.communicate()
 
  ## Small hack for opam to prefers the "faked' compilers
 
    cmd = [options['opam'],'remote'] + opamflags + ['remove','opam_compilers']
    print ' '.join(cmd)
    proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env=env)
    proc.communicate()
 
    cmd = [options['opam'],'remote','add'] + opamflags + ['-p','20','opam_compilers', options['opamcomp']]
    print ' '.join(cmd)
    proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env=env)
    proc.communicate()

    cmd = [options['opam'],'update'] + opamflags
    print ' '.join(cmd)
    proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env=env)
    proc.communicate()

    for version in options['versions'] :
        cmd = [options['opam'],'switch'] + opamflags + [version]
        print ' '.join(cmd)
        proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env=env)
        proc.communicate()


def runopam(reportdir,options):
    env={'OPAMROOT' : options['opamroot']}
    switches=options['versions']
    if options['nocache'] and os.path.exists(reportdir) :
        shutil.rmtree(reportdir)

    if options['nocache'] or not os.path.exists(reportdir) :
        print "Update Opam"
        if not os.path.exists(reportdir) :
            os.makedirs(reportdir,mode=0755)
        cmd = [options['opam'],'update','--quiet','--use-internal-solver']
        print ' '.join(cmd)
        proc = Popen(cmd,stdout=FNULL, stderr=STDOUT, env=env)
        proc.communicate()
    else :
        print "Skip Opam update. Using cache"

    for switch in switches :
        print "Switch %s" % switch

        outfile=os.path.join(reportdir,"report-%s.pef"  % switch)
        if options['nocache'] or not os.path.exists(outfile) :
            print "Saving pef in %s" % outfile
            cmd = [options['opam'],'config','pef-universe','--quiet','--use-internal-solver','--switch',switch]
            print ' '.join(cmd)

            with open(outfile,'w') as f :
                proc = Popen(cmd, stdout=f, env=env)
                proc.communicate()
                f.close()
        else :
            print "Using Cache report-%s.pef"  % switch

        inputfile = outfile
        outfile=os.path.join(reportdir,"report-%s.yaml" % switch)
        if options['nocache'] or not os.path.exists(outfile) :
            print "Running Distcheck %s" % outfile
            cmd = [options['distcheck'],'-f','-s','-tpef', inputfile]
            print ' '.join(cmd)
            with open(outfile,'wa+') as f :
                f.write("ocaml_switch: %s\n" % switch)
                f.flush()

                proc = Popen(cmd, stdout=f)
                proc.communicate()
                f.close()
        else :
            print "Using Cache report-%s.yaml"  % switch

def replay(commit,options) : 
    print "Checkout Commit %s" % commit
    if not os.path.exists(os.path.dirname(options['opamrepo'])):
        initrepo(options)

    repo = git.Repo(options['opamrepo'])
    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.remotes.origin.fetch()
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

def load_and_parse(reportdir,commit1,commit2,options):
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

    def run(reportdir, options) :
        picklefile = os.path.join(reportdir,'data.pickle')
        print "Load and Parse : %s" % reportdir
        if not os.path.exists(reportdir) :
            os.makedirs(reportdir,mode=0755)
        if options['nocache'] and os.path.exists(picklefile) :
            os.remove(picklefile)

        if os.path.exists(picklefile) :
            print "Load Cache %s" % picklefile
            with open(picklefile,'r') as f :
                ro = sorted(pickle.load(f),key=lambda r: r['switch'])
        else :
            ro = sorted(get(reportdir),key=lambda r: r['switch'])
            s = signal.signal(signal.SIGINT, signal.SIG_IGN)
            with open(picklefile,'wb') as f :
                pickle.dump(ro,f)
                f.close()
            signal.signal(signal.SIGINT, s)
        return ro

    ro1 = run(os.path.join(reportdir,commit1),options)
    ro2 = run(os.path.join(reportdir,commit2),options)

    return (zip(ro1,ro2))

def printset(commit,report) :
    for r in report :
        print "Switch: %s" % r['switch']
        if len(r['new']) > 0 :
            print "These packages are NEW in %s" % commit
            for (n,v) in r['new'] :
                print "(%s,%s)" % (n,v)

        if len(r['rem']) > 0 :
            print "These packages were REMOVED in %s" % commit
            for (n,v) in r['rem'] :
                print "(%s,%s)" % (n,v)

        if len(r['fixed']) > 0 :
            print "These packages were FIXED in %s" % commit
            for (n,v) in r['fixed'] :
                print "(%s,%s)" % (n,v)

        if len(r['broken']) :
            print "These packages are now BROKEN in %s" % commit
            for (n,v) in r['broken'] :
                print "(%s,%s)" % (n,v)

    print
 

def compare(reportdir,commit1,commit2,options) :
    print "Comparing reports %s - %s" % (commit1,commit2)
    d = []
    for (r1,r2) in load_and_parse(reportdir,commit1,commit2,options) :
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
#    printset(commit1,d)

    return d

def run(commit1,commit2,options) :

    reportdir = tempfile.mkdtemp('ows-diff')
    reportdir = options['owscache']

    replay(commit1,options)
    runopam(os.path.join(reportdir,commit1),options)

    replay(commit2,options)
    runopam(os.path.join(reportdir,commit2),options)

    d = compare(reportdir,commit1,commit2,options)
    return d

def patch(commit,patchfile,options):
    newbranch="ows-travis-branch"
    author=git.Actor("ows", "ows@irill.org")

    if not os.path.exists(os.path.dirname(options['opamrepo'])):
        initrepo(options)

    repo = git.Repo(options['opamrepo'])
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

    diff = run(commit,str(repo.commit()),options)

    d = os.path.join(options['owscache'],str(repo.commit()))
    if os.path.exists(d) :
        shutil.rmtree(d)

    repo.git.reset('--hard')
    repo.git.clean('-xdf')
    repo.git.checkout('master')
    repo.git.branch('-D',newbranch)

    return diff

def source(owsconf):

    command = ['bash', '-c', 'set -a && source %s && env' % owsconf ]
    proc = Popen(command, stdout=PIPE)
    for line in proc.stdout:
      (key, _, value) = line.partition("=")
      os.environ[key] = value.strip()
    proc.communicate()

    return os.environ

def main():
    if os.getenv('DEFAULTS') :
        os.environ = source(os.getenv('DEFAULTS'))
    print os.getenv('DATADIR','/tmp')

    parser = argparse.ArgumentParser(description='Confront two distcheck reports')
    parser.add_argument('--nocache', action='store_true', default=False)
    parser.add_argument('--repo', nargs=1, default=[os.getenv('DATADIR','/tmp')])
    parser.add_argument('--giturl', nargs=1, default=['git://github.com/ocaml/opam-repository'])
    parser.add_argument('--opam', nargs=1, default=[os.getenv('OPAM','opam')])
    parser.add_argument('--distcheck', nargs=1, default=[os.getenv('DISTCHECK','dose-distcheck')])
    subparsers = parser.add_subparsers(dest='cmd')
    init_parser = subparsers.add_parser('init')
    diff_parser = subparsers.add_parser('diff')
    diff_parser.add_argument('commit1', nargs=1, help="reference commit (git ref)")
    diff_parser.add_argument('commit2', nargs=1, help="new commit (git ref)")
    args = parser.parse_args()

    reponame = (urlparse(args.giturl[0]).netloc + urlparse(args.giturl[0]).path).replace("/","-")
    VERSIONS = "3.12.1 4.00.1 4.01.0 4.02.0 4.02.1"
    options = {
            'versions'  : os.getenv('VERSIONS',VERSIONS).split(),
            'distcheck' : args.distcheck[0],
            'opam'      : args.opam[0],
            'opamrepo'  : os.path.join(args.repo[0],reponame,"opam-repository"),
            'opamroot'  : os.path.join(args.repo[0],reponame,"opam-root"),
            'opamcomp'  : os.path.join(args.repo[0],reponame,"opam-compilers"),
            'owscache'  : os.path.join(args.repo[0],reponame,"cache"),
            'giturl'    : args.giturl[0],
            'nocache'   : args.nocache
    }

    print options

    if args.cmd == 'init' or not os.path.exists(options['opamroot']) :
        initrepo(options)

    if args.cmd == 'diff' :
        commit1 = args.commit1[0]
        commit2 = args.commit2[0]
        d = run(commit1,commit2,options)
        printset(commit2,d)
       
if __name__ == '__main__':
    main()
