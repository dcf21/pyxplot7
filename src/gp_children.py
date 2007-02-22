# GP_CHILDREN.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
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

# Signal handler for calling wait() to eliminate zombies.  We do this in a
# separate process, to foster gp_persist sessions even after PyXPlot itself
# quits.

# We don't use SIGCHLD as this would break os.popen....
# http://twistedmatrix.com/trac/ticket/733
# http://mail.python.org/pipermail/python-dev/2004-November/049987.html

import signal
import re
import os
import sys
import time

import gp_settings
import gp_version
import gp_error

# Communications files which link PyXPlot to the CSA

gv_errorfile_fn  = "%s/gv_errors"%gp_settings.tempdir
gv_errorfile     = open(gv_errorfile_fn, "a") # File where ghostview errors get sent
gv_errorfile_pos = 0
gv_errorfile_stat= None

csa_cmd_fn  = "%s/csa_cmd"%gp_settings.tempdir
csa_cmd     = open(csa_cmd_fn, "a") # File where PyXPlot sends commands to CSA
csa_cmd_pos = 0
csa_cmd_stat= None

# -----------------------------------------------------------------------------------------
# --- Functions called by PyXPlot to drive the CSA, or to read data coming back from it ---
# -----------------------------------------------------------------------------------------

# STAT_GV_OUTPUT(): A magic function for feeding gv stderr messages through to
# the console, without getting SIGTERM messages as well.

def stat_gv_output():
 global gv_errorfile_pos, gv_errorfile_stat
 latest_stat = os.stat(gv_errorfile_fn)[8:9] # [st_mtime, st_ctime]
 if (latest_stat == gv_errorfile_stat): return
 i=0
 for line in open(gv_errorfile_fn,"r"):
  l = line.strip()
  if (i>=gv_errorfile_pos) and (len(l)>0) and (re.search("signal %d"%signal.SIGTERM,l)==None): gp_error.gp_error(l)
  i+=1
 gv_errorfile_pos  = i
 gv_errorfile_stat = latest_stat

# SEND_COMMAND_TO_CSA(): commands are...
#      0 -- start a gv_singlewindow session
#      1 -- start a gv_multiwindow session
#      2 -- start a gv_persist session
#      A -- clear command; wipe any gv_singlewindow session which may be open
#      B -- The CSA is hereby informed that PyXPlot has quit...

def send_command_to_csa(command, string):
 csa_cmd.write("%s%s\n"%(command[0], string))
 csa_cmd.flush()

# -------------------------------------------------------------------------------------
# --- Private functions of the CSA. These are only to be called by the CSA process. ---
# -------------------------------------------------------------------------------------

# The following routine fires up a separate background process. It monitors X11
# ghostview sessions, and removes our temporary working directory only when
# they have all of the X11_persist sessions have quit.

ghostviews         = []   # List of X11_multiwindow and X11_singlewindow sessions which we slaughter on PyXPlot exit
ghostview_persists = []   # List of X11_persist sessions for which we leave our temporary directory for until they quit
ghostview_pid      = None # pid of any running gv process launched under X11_singlewindow
ghostview_fname    = None
pyxplot_running    = True

def child_support_agency_init():
 fork = os.fork()
 if (fork != 0):
  return # Parent process
 else:
  os.chdir(gp_settings.tempdir)
  csa_main() # Child process
  os._exit(0)

def csa_main():
 while pyxplot_running or (ghostview_persists != []):
  try:
   time.sleep(1) # Wake up every second
   csa_check_for_child_exits()
   csa_command_stat() # Check for orders from PyXPlot
  except KeyboardInterrupt: pass
 os.chdir("/tmp") # Remove temporary directory
 gv_errorfile.close()
 csa_cmd.close()
 os.system("rm -Rf %s"%gp_settings.tempdir)

def csa_check_for_child_exits():
 global ghostview_pid
 for gv_list in [ghostviews, ghostview_persists]:
  for ghostview in gv_list:
   output = os.waitpid(ghostview, os.WNOHANG)
   if (output != (0,0)): # Stabat mater dolorosa
    gv_list.remove(ghostview)
    if (ghostview == ghostview_pid): ghostview_pid = None

def csa_command_stat():
 global csa_cmd_pos, csa_cmd_stat, ghostview_fname, ghostview_pid, pyxplot_running
 cmd_for_processing = []
 latest_stat = os.stat(csa_cmd_fn)[8:9] # [st_mtime, st_ctime]
 if (latest_stat == csa_cmd_stat): return
 i=0
 for line in open(csa_cmd_fn,"r").readlines():
  if (i>=csa_cmd_pos) and (len(line.strip())>0): cmd_for_processing.append(line.strip())
  i+=1

 for cmd in cmd_for_processing:
  if   (cmd[0] == "A"): csa_kill_gv_sw() # clear command executed
  elif (cmd[0] == "B"):                  # PyXPlot quit
   csa_massacre_children()
   pyxplot_running = False
  elif (cmd[0] == "0"):                  # gv_singlewindow
   if (ghostview_pid != None):
    os.system("cp -f %s %s"%(cmd[1:], ghostview_fname))
   else:
    ghostview_fname = cmd[1:]
    ghostview_pid   = csa_fork_gv(cmd[1:], ghostviews)
  elif (cmd[0] == "1"):                  # gv_multiwindow
   csa_fork_gv(cmd[1:], ghostviews)
  elif (cmd[0] == "2"):                  # gv_persist
   csa_fork_gv(cmd[1:], ghostview_persists)

 csa_cmd_pos  = i # Do this at the end; if we get SIGINT whilst working, it means we do things twice rather than not at all
 csa_cmd_stat = latest_stat

def csa_fork_gv(fname, gv_list):
 fork = os.fork()
 if (fork != 0):
  gv_list.append(fork)
  return fork
 else:
  os.dup2(gv_errorfile.fileno(), sys.stderr.fileno()) # Stop ghostview from spamming terminal
  os.execlp(gp_version.GHOSTVIEW, gp_version.GHOSTVIEW, '--watch', "%s"%fname)
  os._exit(0)

def csa_massacre_children():
 global ghostviews, ghostview_pid
 for ghostview in ghostviews:
  os.kill(ghostview, signal.SIGTERM) # Dulce et decorum est pro patria mori
 csa_check_for_child_exits()

def csa_kill_gv_sw(): # Used by the 'clear' command to close an X11_singlewindow window
 global ghostview_pid
 if (ghostview_pid != None): os.kill(ghostview_pid, signal.SIGTERM) # Kill gv session
 csa_check_for_child_exits()

# Start up the Child Support Agency
child_support_agency_init()
