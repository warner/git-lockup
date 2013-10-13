
import os, sys, re, subprocess, tempfile, shutil, unittest

scriptdir = os.path.abspath("build/scripts-%d.%d" % (sys.version_info[:2]))
ga = os.path.join(scriptdir, "git-assure")
if not os.path.isdir(scriptdir) or not os.path.exists(ga):
    print "'git-assure' script is missing: please run 'setup.py build'"
    sys.exit(1)
os.environ["PATH"] = os.pathsep.join([scriptdir]+
                                     os.environ["PATH"].split(os.pathsep))

class RunnerMixin:
    VERBOSE = False
    def run_command(self, args, cwd=None, verbose=False):
        # this command is expected to succeed. If it fails, we display
        # stderr.
        if verbose or self.VERBOSE:
            print "COMMAND:", args
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except EnvironmentError:
            e = sys.exc_info()[1]
            print("unable to run %s" % args[0])
            print(e)
            raise
        stdout,stderr = p.communicate()
        if sys.version >= '3':
            stdout = stdout.decode()
            stderr = stderr.decode()
        if verbose or self.VERBOSE:
            print " rc:", p.returncode
            print " out: '%s'" % stdout
            print " err: '%s'" % stderr
        if p.returncode != 0:
            print("unable to run %s (error)" % args[0])
            print("stderr: '%s'" % stderr)
            raise ValueError("command failed")
        return stdout

    def run_failing_command(self, args, cwd=None, verbose=False):
        # this is expected to fail, with rc != 0
        if verbose or self.VERBOSE:
            print "COMMAND:", args
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except EnvironmentError:
            e = sys.exc_info()[1]
            print("unable to run %s" % args[0])
            print(e)
            raise
        stdout,stderr = p.communicate()
        if sys.version >= '3':
            stdout = stdout.decode()
            stderr = stderr.decode()
        if verbose or self.VERBOSE:
            print " rc:", p.returncode
            print " out: '%s'" % stdout
            print " err: '%s'" % stderr
        return (p.returncode, stdout, stderr)

class BasedirMixin:
    def make_basedir(self, testname):
        basedir = os.path.join("_test_temp", testname)
        if os.path.isdir(basedir):
            shutil.rmtree(basedir)
        os.makedirs(basedir)
        return basedir

class Create(BasedirMixin, RunnerMixin, unittest.TestCase):

    def subpath(self, path):
        return os.path.join(self.basedir, path)
    def git(self, *args, **kwargs):
        workdir = kwargs.pop("workdir",
                             self.subpath(kwargs.pop("subdir", "demo")))
        assert not kwargs, kwargs.keys()
        output = self.run_command(["git"]+list(args), workdir)
        return output.strip()

    def add_change(self, subdir="one", message="more"):
        with open(os.path.join(self.subpath(subdir), "README"), "a") as f:
            f.write(message+"\n")
        self.git("add", "README", subdir=subdir)
        self.git("commit", "-m", message, subdir=subdir)

    def test_run(self):
        out = self.run_command(["git-assure", "--help"])
        self.assertIn("git-assure understands the following commands", out)
        self.assertIn("setup-publish: run in a git tree, configures for push", out)
        self.assertIn("extract-tool WHERE: writes 'assure-tool' to WHERE", out)

    def test_setup(self):
        self.basedir = self.make_basedir("Create.setup")
        upstream = self.subpath("upstream")
        os.makedirs(upstream)
        one = self.subpath("one")
        self.git("init", "--bare", subdir="upstream")
        self.git("clone", os.path.abspath(upstream), os.path.abspath(one),
                 workdir=upstream)
        self.add_change(message="initial-unsigned")
        self.git("push", subdir="one")
        out = self.run_command(["git-assure", "setup-publish"], one)
        self.assertIn("the post-commit hook will now sign changes on branch 'master'", out)
        self.assertIn("verifykey: vk0-", out)
        vk_s = re.search(r"(vk0-\w+)", out).group(1)
        #self.assertIn("you should now commit the generated 'setup-assure'", out)
        self.git("add", "setup-assure", subdir="one")

        # pyflakes one/.git/assure-tool
        # pyflakes one/setup-assure

        # now that the publishing repo is configured to sign commits, adding
        # a change should get a note with a signature
        self.add_change(message="first-signed")
        head = self.git("rev-parse", "HEAD", subdir="one")
        notes = self.git("notes", "list", head, subdir="one").split("\n")
        self.assertEqual(len(notes), 1, notes)

        # the updated refspec should push the notes along with the commits
        self.git("push", subdir="one")

        # so they should be present in the upstream (bare) repo
        notes = self.git("notes", "list", head, subdir="upstream").split("\n")
        self.assertEqual(len(notes), 1, notes)

        # cloning the repo doesn't get the notes by default
        two = self.subpath("two")
        self.git("clone", os.path.abspath(upstream), os.path.abspath(two),
                 workdir=upstream)
        notes = self.git("notes", subdir="two")
        self.assertEqual(notes, "")

        # run the downstream setup script
        out = self.run_command([sys.executable, "./setup-assure"], two)
        self.assertIn("remote 'origin' configured to use verification proxy", out)
        self.assertIn("branch 'master' configured to verify with key %s" % vk_s, out)

        # now downstream pulls should work, fetch notes, and check signatures
        out = self.git("pull", subdir="two")
        #self.assertNotIn("Could not find local refs/notes/commits", out)
        #print "FIRST PULL", out

        self.add_change(message="second-signed")
        self.git("push", subdir="one")
        out = self.git("pull", subdir="two")
        #print "SECOND PULL", out
        one_head = self.git("rev-parse", "HEAD", subdir="one")
        two_head = self.git("rev-parse", "HEAD", subdir="two")
        self.assertEqual(one_head, two_head)

        # unsigned commits should be rejected by the downstream
        unsigned = self.subpath("unsigned")
        self.git("clone", os.path.abspath(upstream), os.path.abspath(unsigned),
                 workdir=upstream)
        self.add_change(subdir="unsigned", message="unsigned")
        unsigned_head = self.git("rev-parse", "HEAD", subdir="unsigned")
        self.assertNotEqual(unsigned, one_head)
        self.git("push", subdir="unsigned")

        rc,out,err = self.run_failing_command(["git", "pull"],
                                              self.subpath("two"))
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("\nno valid signature found for branch refs/heads/master (rev %s)\n" % unsigned_head, err)
        self.assertIn("\nfatal: Could not read from remote repository.\n", err)
        # should fail

        #print "THIRD PULL (unsigned)", out
        two_head = self.git("rev-parse", "HEAD", subdir="two")
        self.assertNotEqual(two_head, unsigned_head)

if __name__ == "__main__":
    unittest.main()
