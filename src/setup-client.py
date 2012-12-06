
def setup_client(args):
    remote, branch, url, key = args

    ext_url = "ext::.git/assure-tool fetch %s %s" % (remote, url)

    oldurl = get_config("remote.%s.url" % remote)
    if oldurl and oldurl != ext_url:
        print "eek, remote '%s' has scary URL '%s'" % (remote, oldurl)
        sys.exit(1)
    run_command(["git", "config", "remote.%s.url" % remote, ext_url])
    print "remote '%s' configured to use verification proxy" % remote

    verfkeys = get_all_config("branch.%s.assure-key" % branch)
    if key in verfkeys:
        print "branch '%s' was already configured to verify with key %s" % (branch, key)
    else:
        run_command(["git", "config", "--add", "branch.%s.assure-key" % branch, key])
        print "branch '%s' configured to verify with key %s" % (branch, key)
