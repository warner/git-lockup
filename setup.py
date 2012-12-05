#!/usr/bin/env python

from distutils.core import setup
from distutils.command.build_scripts import build_scripts

import versioneer
versioneer.versionfile_source = "src/_version.py"
versioneer.versionfile_build = "src/_version.py"
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

class my_build_scripts(build_scripts):
    pass

commands["build_scripts"] = my_build_scripts

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
