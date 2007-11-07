# GP_TABULATE.PY
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

# Implementation of tabulate command

import gp_datafile
import gp_settings
import gp_math
import gp_version
from gp_error import *

import os
import sys
from math import *
import glob
import re
import time


# Counters used to cycle plot styles
withstate = 0 # State parameter used when processing input after the word "with"

# Only warn user once about the using modifier when plotting functions
using_use_warned = False

# DIRECTIVE_TABULATE(): Handles the 'tabulate' command

def directive_tabulate(command,vars,settings):
  # First allocate an x-axis and a y-axis, the two axes we have by default
  axes = { 'x':{}, 'y':{}, 'z':{} }
  for dir in ['x', 'y']:
   axes[dir][1] = gp_settings.axes[dir][1].copy()

  # If requested, change the ranges of these axes
  for i in range(min(1, len(command['range_list']))):
   if ((i%2) == 0): direction='x'
   else           : direction='y'
   number=int(i/2)+1
   if 'min' in command['range_list'][i]: axes[direction][number]['MIN'] = command['range_list'][i]['min']
   if 'max' in command['range_list'][i]: axes[direction][number]['MAX'] = command['range_list'][i]['max']

  # Step 1: Work out the ranges of the data, to decide how to autoscale.
  #         This is achieved with a dry-run of the plotting process.
  any_autoscaling_axes = 0
  for direction in 'x', 'y':
   number = 1
   axis = axes[direction][number]
   axis['MIN_USED'] = axis['MIN']
   axis['MAX_USED'] = axis['MAX']
   axis['AXIS']     = None
   axis['LINKINFO'] = {}
   if (axis['LOG'] == "ON"):
    if (axis['MIN_USED'] != None) and (axis['MIN_USED'] <= 0.0):
     axis['MIN_USED'] = None
     axis['MIN'] = None
     gp_warning("Warning: Log axis %s%d set with range minimum < 0 -- this is impossible, so autoscaling instead."%(direction,number))
    if (axis['MAX_USED'] != None) and (axis['MAX_USED'] <= 0.0):
     axis['MAX_USED'] = None
     axis['MAX'] = None
     gp_warning("Warning: Log axis %s%d set with range maximum < 0 -- this is impossible, so autoscaling instead."%(direction,number))

   if ((axis['MIN_USED'] == None) or (axis['MIN_USED'] == None)):
    any_autoscaling_axes = 1

  # Read in details supplied on the commandline

  # Read datafile filename
  if 'filename' in command:
   datafile = command['filename']
  else:
   functions = [item['expression'] for item in command['expression_list:'] ]

  # every
  if 'every_list:' in command: every = command['every_list:']
  else                       : every = []

  # index
  if 'index' in command: index = int(command['index'])
  else                 : index = -1 # default

  # select
  if 'select_criterion' in command: select_criteria = command['select_criterion']
  else                            : select_criteria = ''
  select_cont = True
  if (('select_cont' in command) and (command['select_cont'][0] == 'd')):
   select_cont = False

  # Using rows or columns
  if   'use_rows'    in command: usingrowcol = "row"
  elif 'use_columns' in command: usingrowcol = "col"
  else                         : usingrowcol = "col" # default

  # using
  if 'using_list:' in command: using = [item['using_item'] for item in command['using_list:']]
  else                       : using = []

  # format string
  if 'format' in command: format = command['format']
  else                  : format = ''

  if 'filename' in command:  # We are plotting a datafile...
   datagrid = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, select_cont, every, vars, "tabulate", True, None)
  else: # We are plotting a function...
   if (axes['x'][1]['MIN'] == None): # Automatic range choices
    if (axes['x'][1]['LOG'] == 'ON'):
     if (axes['x'][1]['MAX'] != None): axes['x'][1]['MIN'] = axes['x'][1]['MAX'] / 100 # Log axes start from 1
     else                : axes['x'][1]['MIN'] = 1.0
    else:
     if (axes['x'][1]['MAX'] != None): axes['x'][1]['MIN'] = maximum - 20
     else                : axes['x'][1]['MIN'] = -10.0         # Lin axes start from -10
   if (axes['x'][1]['MAX'] == None):
    if (axes['x'][1]['LOG'] == 'ON'): axes['x'][1]['MAX'] = axes['x'][1]['MIN'] * 100
    else                                             : axes['x'][1]['MAX'] = axes['x'][1]['MIN'] + 20

   # Obtain a raster
   if (axes['x'][1]['LOG'] == 'ON'): xrast = gp_math.lograst(axes['x'][1]['MIN'], axes['x'][1]['MAX'], settings['SAMPLES'])
   else:                             xrast = gp_math.linrast(axes['x'][1]['MIN'], axes['x'][1]['MAX'], settings['SAMPLES'])
   
   # Obtain the data grid for a function
   datagrid = gp_datafile.gp_function_datagrid(xrast, functions, 'x', usingrowcol, using, select_criteria, select_cont, every, vars, 'tabulate', True, None)
  
  # Filter the data to remove any datapoints which fall outside the range of the axes
  datagrid = filter_dataset(datagrid, axes)

  if (len(datagrid) == 1):
   gp_warning("Warning: No data to tabulate!")
   return

  # Print the data out
  output_table(datagrid[1:], settings, format)
  return

# FILTER_DATASET(): Filter data against the ranges supplied

def filter_dataset (datagrid, axes):
 newgrid = []
 for [rows, cols, block] in datagrid:
  newblock = []
  for line in block:
   x = line[0]
   if (x < axes['x'][1]['MIN'] or (axes['x'][1]['MAX'] != None and x > axes['x'][1]['MAX'])):
    rows -= 1
   else:
    newblock.append(line)
  newgrid.append([rows, cols, newblock])
 return newgrid

# OUTPUT_TABLE(): Write the table of numbers produced out to a file

def output_table (datagrid, settings, format):
  # Get the filename
  fname_out = os.path.expanduser(settings['OUTPUT'])
  if (fname_out == ""): fname_out = "pyxplot.dat"
  outfile = os.path.join(gp_settings.cwd, os.path.expanduser(fname_out))

  # Create backup of pre-existing datafile if necessary
  if( settings['BACKUP']=="ON") and os.path.exists(outfile):
   i=0
   while os.path.exists("%s~%d"%(outfile,i)): i+=1
   os.rename(outfile,"%s~%d"%(outfile,i))

  f = open(outfile, 'w') # Open output datafile

  # Write a header
  f.write("# Datafile produced by PyXPlot %s on %s\n"%(gp_version.VERSION,time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())))

  # Produce a format string.
  cols = datagrid[0][1]
  formats = []
  formatprefix = ''
  # Test for a user-supplied string
  if (format != ''):
   # Check that this is a format string and extract an optional prefix
   test = re.search(r'^([^%]*)%', format)
   if (test == None):
    gp_error("Error: Bad format string %s"%format)
    return []
   formatprefix = test.group(1)
   # Extract the format substrings from it
   formatitems = re.findall(r'%[^%]*', format)
   Nformatitems = len(formatitems)
   formats = [formatitems[i%Nformatitems] for i in range(cols)]
  else:
   formats = ["%16s" for i in range(cols)]

  # Actually write the data file
  try:
   for [rows, cols, block] in datagrid:
    for line in block:
     strs = [formatprefix]
     for i in range(len(line)):
      format = formats[i]
      if (format[-1] == 'd'):
       strs.append(formats[i]%int(line[i]))
      else: 
       strs.append(formats[i]%line[i])
     str = ' '.join(strs)
     f.write("%s\n"%str)
    f.write("\n")
  except:
   gp_error("Error whilst writing tabulated file.")
   raise

  f.close()
  return
