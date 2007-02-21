# GP_ERROR.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
#
# $Id: gp_error.py,v 1.20 2007/02/21 03:48:00 dcf21 Exp $
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

# Error handler

import sys
import traceback

# Print traceback on error?

DEBUG = False

# Used to inform user of line number of errors in scripts

gp_error_input_linenumber = -1
gp_error_input_filename   = ""
gp_error_last_linenumber  = gp_error_input_linenumber # Only inform user one of each line number
gp_error_last_filename    = gp_error_input_filename

def gp_error_setstreaminfo(linenumber,filename):
  global gp_error_input_linenumber,gp_error_input_filename
  gp_error_input_linenumber = linenumber
  gp_error_input_filename = filename

# Colour error messages?
# These options are overwritten in gp_settings

gp_termcol     = False
gp_termcol_err = gp_termcol_wrn = gp_termcol_rep = "Normal"

def gp_error_setnocolour():  global gp_termcol     ; gp_termcol     = False
def gp_error_setcolour():    global gp_termcol     ; gp_termcol     = True
def gp_error_setrepcol(col): global gp_termcol_rep ; gp_termcol_rep = col
def gp_error_setwrncol(col): global gp_termcol_wrn ; gp_termcol_wrn = col
def gp_error_seterrcol(col): global gp_termcol_err ; gp_termcol_err = col

# We import this here, as gp_settings actually uses the above functions, so we need to define them first!
import gp_settings

# A fairly minimal error handler, which sends error messages to stderr
# and report messages to stdout

def gp_error(*text):
  global gp_error_last_linenumber, gp_error_last_filename

  if (gp_error_input_linenumber not in [-1,gp_error_last_linenumber]) or (gp_error_input_filename not in ["",gp_error_last_filename]):
    [gp_error_last_filename,gp_error_last_linenumber] = [gp_error_input_filename,gp_error_input_linenumber]
    gp_error("Error encountered in %s at line %d:"%(gp_error_input_filename,gp_error_input_linenumber))

  print_item = ""
  for item in text: print_item += str(item)+" "
  if gp_termcol and sys.stderr.isatty():
    print_item = gp_settings.terminal_colours[gp_termcol_err] + print_item + gp_settings.terminal_colours["Normal"]
  sys.stderr.write(print_item+"\n")
  # if DEBUG: traceback.print_stack(limit=5)
  if DEBUG: traceback.print_tb(sys.exc_info()[2],limit=5)

def gp_warning(*text):
  print_item = ""
  for item in text: print_item += str(item)+" "
  if gp_termcol and sys.stderr.isatty():
    print_item = gp_settings.terminal_colours[gp_termcol_wrn] + print_item + gp_settings.terminal_colours["Normal"]
  sys.stderr.write(print_item+"\n")

def gp_report(*text):
  print_item = ""
  for item in text: print_item += str(item)+" "
  if gp_termcol and sys.stdout.isatty():
    print_item = gp_settings.terminal_colours[gp_termcol_rep] + print_item + gp_settings.terminal_colours["Normal"]
  sys.stdout.write(print_item+"\n")
