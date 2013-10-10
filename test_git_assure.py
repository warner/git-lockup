
import os, sys, subprocess, tempfile, shutil, unittest

scriptdir = os.path.abspath("build/scripts-%d.%d" % (sys.version_info[:2]))
ga = os.path.join(scriptdir, "git-assure")
if not os.path.isdir(scriptdir) or not os.path.exists(ga):
    print "'git-assure' script is missing: please run 'setup.py build'"
    sys.exit(1)
os.environ["PATH"] = os.pathsep.join([scriptdir]+
                                     os.environ["PATH"].split(os.pathsep))

def run_command(args, cwd=None, verbose=False, hide_stderr=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE,
                             stderr=(subprocess.PIPE if hide_stderr else None))
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout

class BasedirMixin:
    def make_basedir(self, testname):
        basedir = os.path.join("_test_temp", testname)
        if os.path.isdir(basedir):
            shutil.rmtree(basedir)
        os.makedirs(basedir)
        return basedir

class Create(BasedirMixin, unittest.TestCase):

    def subpath(self, path):
        return os.path.join(self.basedir, path)
    def git(self, *args, **kwargs):
        workdir = kwargs.pop("workdir",
                             self.subpath(kwargs.pop("subdir", "demo")))
        assert not kwargs, kwargs.keys()
        output = run_command(["git"]+list(args), workdir, True)
        if output is None:
            self.fail("problem running git")
        return output

    def add_change(self, subdir="one"):
        with open(os.path.join(self.subpath(subdir), "README"), "a") as f:
            f.write("more\n")
        self.git("add", "--all", subdir=subdir)
        self.git("commit", "-m", "message", subdir=subdir)

    def test_run(self):
        out = run_command(["git-assure", "--help"], verbose=True)
        self.assertIn("git-assure understands the following commands", out)
        self.assertIn("setup-publish: run in a git tree, configures for push", out)
        self.assertIn("extract-tool WHERE: writes 'assure-tool' to WHERE", out)

    def test_setup(self):
        self.basedir = self.make_basedir("Create.setup")
        os.makedirs(self.subpath("one"))
        print self.subpath("one")
        self.git("init", subdir="one")
        self.add_change()
        print run_command(["git-assure", "setup-publish"])

if __name__ == "__main__":
    unittest.main()
