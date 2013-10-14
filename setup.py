#!/usr/bin/env python

import os, base64
from distutils.core import setup, Command
from distutils.command.build_scripts import build_scripts

import versioneer
versioneer.versionfile_source = "src/_version.py"
versioneer.versionfile_build = "VERSIONFILE_BUILD"
versioneer.tag_prefix = ""
versioneer.parentdir_prefix = "git-assure-"

LONG_DESCRIPTION="""\
Sign+verify author signatures on git commits.

By running one command, developers who publish changes to a public git
repository will automatically add signatures to each revision. Followers who
clone the repo can run one command to setup automatic checking of those
signatures. Once enabled, followers will only accept genuine commits from the
upstream author(s).

Signatures are created in a post-commit hook, and stored (one line per
revision) using the "git-notes" feature, where they can be pushed and fetched
just like regular branches. On the receiving side, the signatures are checked
before the remote tracking branch is ever modified, so all "git fetch" and
"git pull" commands that reference the specific remote will be safe.

The tools require python but no other dependencies.
"""

commands = versioneer.get_cmdclass().copy()
commands = {} # disable for now

substitutions = {}
def construct(source):
    output = []
    f = open(os.path.join("src", source))
    for line in f.readlines():
        if line.startswith("#tmp "):
            continue
        if line.startswith("#<--"):
            name = line.replace("#<--", "").strip()
            if name not in substitutions:
                raise ValueError("unrecognized substitution '%s' in '%s'" % (name, source))
            if not name.endswith("-b64"):
                output.append("##### == BEGIN %s ==\n" % name)
            output.append(substitutions[name])
            if not name.endswith("-b64"):
                output.append("##### == END %s ==\n" % name)
        else:
            output.append(line)
    return "".join(output)
def add_substitution(name, source):
    substitutions[name] = construct(source)
def add_base64_substitution(name, source):
    b64 = base64.b64encode(construct(source))
    lines = [b64[i:i+60] for i in range(0, len(b64), 60)]
    substitutions[name] = "\n".join(lines)+"\n"


class my_build_scripts(build_scripts):
    def run(self):
        tempdir = os.path.join(self.build_dir, "temp")
        if not os.path.isdir(tempdir):
            os.makedirs(tempdir)

        add_substitution("ed25519", "ed25519.py")
        add_substitution("common", "common.py")
        add_base64_substitution("setup-assure-b64", "setup-assure-template")

        git_assure = os.path.join(self.build_dir, "temp", "git-assure")
        print "creating", git_assure
        f = open(git_assure, "w")
        f.write(construct("git-assure-template"))
        f.close()

        # modify self.scripts with the source pathname of scripts to install
        # into self.build_dir . When we upcall, those scripts will be copied
        # and adjusted (their shbang line set to sys.executable).
        self.scripts = [git_assure]
        return build_scripts.run(self)
commands["build_scripts"] = my_build_scripts

class Test(Command):
    description = "run tests"
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import test_git_assure
        test_git_assure.unittest.main(module=test_git_assure, argv=["dummy"])
commands["test"] = Test

setup(name="git-assure",
      version=versioneer.get_version(),
      description="sign+verify git commits",
      long_description=LONG_DESCRIPTION,
      author="Brian Warner",
      author_email="warner-git-assure@lothar.com",
      license="MIT",
      url="https://github.com/warner/git-assure",
      scripts=["src/git-assure"],
      cmdclass=commands,
      )
