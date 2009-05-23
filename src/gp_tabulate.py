# GP_TABULATE.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-9 Dominic Ford <coders@pyxplot.org.uk>
#               2008-9 Ross Church
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
  gridlist = []  # List of grids to output from all functions in list supplied

  # Options that apply to all things to be tabulated: currently only the format string
  if 'format' in command: format = command['format']
  else                  : format = ''
   
  # We need separate axes for function and datafile evaluation (unless axes have been specified completely by the user)
  # This is because file axes are chosen from the data, whereas function axes need to be chosen before the data can be generated
  funcaxes = { 'x':{}, 'y':{}, 'z':{} }
  fileaxes = { 'x':{}, 'y':{}, 'z':{} }
  for dir in ['x', 'y']:
   funcaxes[dir][1] = gp_settings.axes[dir][1].copy()
   fileaxes[dir][1] = gp_settings.axes[dir][1].copy()

  # If requested, change the ranges of these axes
  for i in range(min(1, len(command['range_list']))):
   if ((i%2) == 0): direction='x'
   else           : direction='y'
   number=int(i/2)+1
   if 'min' in command['range_list'][i]: 
    fileaxes[direction][number]['MIN'] = funcaxes[direction][number]['MIN'] = command['range_list'][i]['min']
   if 'max' in command['range_list'][i]: 
    fileaxes[direction][number]['MAX'] = funcaxes[direction][number]['MAX'] = command['range_list'][i]['max']
   if 'minauto' in command['range_list'][i]:
    fileaxes[direction][number]['MIN'] = funcaxes[direction][number]['MIN'] = None
   if 'maxauto' in command['range_list'][i]:
    fileaxes[direction][number]['MAX'] = funcaxes[direction][number]['MAX'] = None

  # Step 1: Set up the axes structure for function evaluation
  for direction in 'x', 'y':
   axis = funcaxes[direction][1]
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

    # Automatic range choices
  if (funcaxes['x'][1]['MIN'] == None): 
   if (funcaxes['x'][1]['LOG'] == 'ON'):
    if (funcaxes['x'][1]['MAX'] != None): funcaxes['x'][1]['MIN'] = funcaxes['x'][1]['MAX'] / 100 # Log axes start from 1
    else                                : funcaxes['x'][1]['MIN'] = 1.0
   else:
    if (funcaxes['x'][1]['MAX'] != None): funcaxes['x'][1]['MIN'] = funcaxes['x'][1]['MAX'] - 20
    else                                : funcaxes['x'][1]['MIN'] = -10.0         # Lin axes start from -10
  if (funcaxes['x'][1]['MAX'] == None):
   if (funcaxes['x'][1]['LOG'] == 'ON'): funcaxes['x'][1]['MAX'] = funcaxes['x'][1]['MIN'] * 100
   else                                : funcaxes['x'][1]['MAX'] = funcaxes['x'][1]['MIN'] + 20
  
  # Obtain a raster
  if (funcaxes['x'][1]['LOG'] == 'ON'): xrast = gp_math.lograst(funcaxes['x'][1]['MIN'], funcaxes['x'][1]['MAX'], settings['SAMPLES'])
  else:                                 xrast = gp_math.linrast(funcaxes['x'][1]['MIN'], funcaxes['x'][1]['MAX'], settings['SAMPLES'])
    
  # Step 2: Assemble our blocks of data to plot
  if not 'tabulate_list,' in command: 
   gp_warning('Nothing to tabulate!')
   return

  # Iterate through each item to tabulate and obtain the corresponding data grid
  for tabulate_item in command['tabulate_list,']:
    
   # every
   if 'every_list:' in tabulate_item: every = tabulate_item['every_list:']
   else                             : every = []
   
   # index
   if 'index' in tabulate_item: index = int(tabulate_item['index'])
   else                       : index = -1 # default
   
   # select
   if 'select_criterion' in tabulate_item: select_criteria = tabulate_item['select_criterion']
   else                                  : select_criteria = ''
   if (('select_cont' in tabulate_item) and (tabulate_item['select_cont'][0] == 'd')): select_cont = False
   else                                                                              : select_cont = True
   
   # Using rows or columns
   if   'use_rows'    in tabulate_item: usingrowcol = "row"
   elif 'use_columns' in tabulate_item: usingrowcol = "col"
   else                               : usingrowcol = "col" # default
   
   # using
   if 'using_list:' in tabulate_item: using = [item['using_item'] for item in tabulate_item['using_list:']]
   else                             : using = []
   
   if 'filename' in tabulate_item:  # We are plotting a datafile...
    datafile = tabulate_item['filename']
    type = 'file'
    datagrid = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, select_cont, every, vars, "tabulate", True, None)
   else: # We are plotting a function...
    functions = [item['expression'] for item in tabulate_item['expression_list:'] ]
    type = 'func'
    if (using != []): type = 'func_using'
    # Obtain the data grid for a function
    datagrid = gp_datafile.gp_function_datagrid(xrast, functions, 'x', usingrowcol, using, select_criteria, select_cont, every, vars, 'tabulate', True, None)
   
   # Filter the data to remove any datapoints which fall outside the range of the axes
   datagrid = filter_dataset(datagrid, fileaxes) # fileaxes is correct here because it's the least restrictive of the two (reflects only user input)
   
   if (len(datagrid) == 1):
    gp_warning("Warning: No data to tabulate!")
    return
   
   gridlist.append([datagrid[1:], type])

  # Step 3: Taking our list of grids of data, make them into one big grid

  # First, deal with the simple case where there is just one grid
  if (len(gridlist)==1): 
   output_table(gridlist[0][0], settings, format)
   return

  # First, functions tabulated without the "using" modifier should have their x raster stripped, other than for the first one
  # This is so, e.g. "tab sin(x),cos(x)" produces three columns
  foundfunc = 0
  for grid in range(len(gridlist)):
   if gridlist[grid][1] != 'func': continue # Check type == func
   if foundfunc==0:
    foundfunc = 1
    continue
   for block in range(len(gridlist[grid][0])): # Iterate over blocks
    gridlist[grid][0][block][1] -= 1  # Subtract one from column count
    for k in range(len(gridlist[grid][0][block][2])):
     del gridlist[grid][0][block][2][k][0] # Delete x raster value from each datum

  # Get rid of the labels telling us what sort of thing each grid is
  for grid in range(len(gridlist)): gridlist[grid] = gridlist[grid][0]
   
  # Check that the block structure is the same for each grid of data.  If not, collapse each one into a single block
  blocks_differ = 0
  blocks = []
  # For each grid, extract the number of rows in each block into "blocks"
  for grid in range(len(gridlist)):
   blocks.append([gridlist[grid][block][0] for block in range(len(gridlist[grid]))])
  # Check that each list of block sizes is identical
  for i in range(1,len(blocks)):
   if (blocks[i] != blocks[0]):
    blocks_differ = 1
    break
  
  if (blocks_differ == 1):
   gp_warning("Warning: Tabulating sets of data that are different sizes.")
   for grid in range(len(gridlist)):
    for block in range(1,len(gridlist[grid])): 
     gridlist[grid][0][0] += gridlist[grid][block][0]  # Sum the row numbers
     gridlist[grid][0][2] += gridlist[grid][block][2] # Catenate the blocks
     del gridlist[grid][block]                        # Delete the old block

   # We have now collapsed each grid into a single block.  But these overall blocks may not have the same length.
   # In that case we pad the ends of the shorter blocks with zeros.
   max_grid_length = gridlist[0][0][0]
   blocks_differ = 0
   for grid in range(1,len(gridlist)):
    if gridlist[grid][0][0] != gridlist[0][0][0]:
     blocks_differ = 1
     max_grid_length = max(max_grid_length, gridlist[grid][0][0])
   # Produce correctly-sized blank points and pad
   for grid in range(len(gridlist)):
    for i in range(gridlist[grid][0][0],max_grid_length): # Append the correct number of blank rows to the block
     point = []
     for i in range(gridlist[grid][0][1]): point.append('') # Produce a set of empty points the same width as the block
     gridlist[grid][0][2].append(point) 
    gridlist[grid][0][0] = max_grid_length

  # Catenate the grids into one large grid
  for grid in range(1,len(gridlist)):
   for block in range(len(gridlist[0])):
    gridlist[0][block][1] += gridlist[grid][block][1]
    for point in range(len(gridlist[grid][block][2])): 
     gridlist[0][block][2][point] += gridlist[grid][block][2][point]
  
  # Print the data out
  output_table(gridlist[0], settings, format)
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
  fname_out = os.path.expanduser(gp_settings.settings_global['OUTPUT'])
  if (fname_out == ""): fname_out = "pyxplot.dat"
  outfile = os.path.join(gp_settings.cwd, os.path.expanduser(fname_out))

  # Create backup of pre-existing datafile if necessary
  if( gp_settings.settings_global['BACKUP']=="ON") and os.path.exists(outfile):
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
   # Produce a default format string for each column of data; ensure that same format is used down whole column for easy readibility.
   allints  = [True for i in range(cols)]
   allsmall = [True for i in range(cols)]
   for [rows, cols, block] in datagrid:
    for line in block:
     for i in range(cols):
      if (line[i]==''): continue # Skip blank points (padding for uneven data grids)
      if (line[i] != float(int(line[i])) or (abs(line[i])>1000)):               allints[i] = False
      if (abs(line[i]) >= 1000 or (abs(line[i]) < .0999999 and line[i] != 0.)): allsmall[i] = False
       
   for i in range(cols):
    if (allints[i]):    formats.append("%10d")
    elif (allsmall[i]): formats.append("%11f")
    else:               formats.append("%15e")
     


  # Actually write the data file
  try:
   for [rows, cols, block] in datagrid:
    for line in block:
     strs = [formatprefix]
     for i in range(len(line)):
      format = formats[i]
      if (line[i]==''): format = "%ss"%format[0:-1] # Change the format string from %XX(d/e/f) to %XXs (sick, eh?)
      if (format[-1] == 'd'): strs.append(format%int(line[i]))
      else:                   strs.append(format%line[i])
     str = ' '.join(strs)
     f.write("%s\n"%str)
    f.write("\n")
  except:
   gp_error("Error whilst writing tabulated file.")
   raise

  f.close()
  return
