import sys, json

data = json.load(sys.stdin)
broken=0
for s in data["result"] :
    if len(s["broken"]) >= 1 :
        broken=1
        print "Broken %s %s" %(s["switch"],s["broken"])
    if len(s["new"]) >= 1 :
        print "New %s %s" %(s["switch"],s["new"])
    if len(s["fixed"]) >= 1 :
        print "Fixed %s %s" %(s["switch"],s["fixed"])
    if len(s["rem"]) >= 1 :
        print "Removed %s %s" %(s["switch"],s["rem"])

sys.exit(broken)

