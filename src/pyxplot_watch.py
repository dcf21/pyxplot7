# PYXPLOT_WATCH.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-8 Dominic Ford <coders@pyxplot.org.uk>
#               2008   Ross Church
#
# $Id$
#
# PyXPlot is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# You should have received a copy of the GNU General Public License along with
# PyXPlot; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA  02110-1301, USA

# ----------------------------------------------------------------------------

import gp_version
import gp_text
from gp_error import *

import os
import sys
import time
import glob

VERSION = gp_version.VERSION
DATE    = gp_version.DATE

version_string = r"""PyXPlot Watch """+VERSION

help_string = r"""PyXPlot Watch """+VERSION+"""

Usage: pyxplot_watch <options> <filelist>
  -v, --verbose: Verbose mode; output full activity log to terminal
  -q, --quiet  : Quiet mode; only output PyXPlot error messages to terminal
  -h, --help   : Display this help
  -V, --version: Display version number"""

watch_files = [] # List of files that we are watching

verbose = False

def do_pyxplot(filename):
  if verbose:
    gp_report("[%s] Running %s."%(time.ctime(),filename)) # In verbose mode, we produce log output
    os.system("pyxplot %s > /dev/null"%filename) # Always discard stdout
    gp_report("[%s] Completed %s."%(time.ctime(),filename))
  else:
    (streamin, streamout, streamerr) = os.popen3("pyxplot %s"%filename)
    stringout = streamout.read()
    stringerr = streamerr.read()
    streamin.close() ; streamout.close() ; streamerr.close()
    if (len(stringerr.strip()) > 0): # In quiet mode, we only produce log output if we encounter an error
      gp_report("[%s] Running %s."%(time.ctime(),filename))
      gp_error(stringerr.strip())
      gp_report("[%s] Completed %s."%(time.ctime(),filename))

# Main Entry Point

try:

# Read filenames from commandline

  helped = False
  for i in range(1,len(sys.argv)):
    if   (sys.argv[i] in ['-h','--help']   ): gp_report(help_string)    ; helped = True
    elif (sys.argv[i] in ['-V','--version']): gp_report(version_string) ; helped = True
    elif (sys.argv[i] in ['-q','--quiet']  ): verbose = False
    elif (sys.argv[i] in ['-v','--verbose']): verbose = True
    else                                    : watch_files.append([sys.argv[i], {}])

  if (len(watch_files) == 0):
    if not helped:
      gp_error("ERROR: No files to watch! Please supply a list of PyXPlot scripts on the commandline.")
      sys.exit(1)
    sys.exit(0) # In case we were called with --help

  if verbose:
    gp_report(gp_text.init)
    gp_report("This is PyXPlot watcher. Press CTRL-C to exit.\nNow watching the following files:")
    for filelist in watch_files: gp_report(filelist[0])
    gp_report("\n--- Activity Log ---")


# PyXPlot each supplied filename straight away

  for [filename,statvals] in watch_files:
   filelist = glob.glob(os.path.expanduser(filename))
   if (len(filelist) == 0): gp_warning("WARNING: Cannot find file '%s'. Will commence watching it when if it appears."%filename)
   for fname in filelist:
    statvals[fname] = os.stat(fname)[8:9] # [st_mtime, st_ctime]
    do_pyxplot(fname)

# Then stat files every two seconds to watch for modification

  while(True):
    time.sleep(2)
    for i in range(len(watch_files)):
      filelist = glob.glob(os.path.expanduser(watch_files[i][0]))
      statvals = {}
      for filename in filelist:
        statvals[filename] = os.stat(filename)[8:9] # [st_mtime, st_ctime]
        if (filename not in watch_files[i][1]) or (statvals[filename] != watch_files[i][1][filename]):
          do_pyxplot(filename)
      watch_files[i][1] = statvals

except KeyboardInterrupt:
  if verbose:
    gp_report("Received keyboard interrupt.")
    gp_report("Quitting.")

