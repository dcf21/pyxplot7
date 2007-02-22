# GP_DATAFILE.PY
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

import gp_eval
import gp_settings
from gp_error import *

import os
import sys
import re
import gzip
import exceptions

try: import scipy
except: SCIPY_ABSENT = True
else: SCIPY_ABSENT = False

ERRORS_MAX = 4

# GP_DATAREAD(): Read a data file, selecting only every nth item from index m, using ....

def gp_dataread(datafile, index, usingrowcol, using_list, select_criterion, every_list, vars, funcs, style, verb_errors=True, firsterror=None):
  rows       = 0
  if (using_list == ''): using_list = gp_settings.datastyleinfo[style][0].split(":")
  using_list = using_list[:]
  for i in range(len(using_list)): using_list[i] = using_list[i].strip()
  columns    = len(using_list)
  if (columns == 1): columns=2
  datagrid   = []
  totalgrid  = [] # List of [file linenumber, line number for spare x-axis, list of data strings]s for all of the blocks that we're going to plot
  vars_local = vars.copy()

  # Parse every list
  if (len(every_list) < 1) or ('every_item' not in every_list[0]): linestep   = 0
  else                                                           : linestep   = every_list[0]['every_item']
  if (len(every_list) < 2) or ('every_item' not in every_list[1]): blockstep  = 0
  else                                                           : blockstep  = every_list[1]['every_item']
  if (len(every_list) < 3) or ('every_item' not in every_list[2]): linefirst  = None
  else                                                           : linefirst  = every_list[2]['every_item']
  if (len(every_list) < 4) or ('every_item' not in every_list[3]): blockfirst = None
  else                                                           : blockfirst = every_list[3]['every_item']
  if (len(every_list) < 5) or ('every_item' not in every_list[4]): linelast   = None
  else                                                           : linelast   = every_list[4]['every_item']
  if (len(every_list) < 6) or ('every_item' not in every_list[5]): blocklast  = None
  else                                                           : blocklast  = every_list[5]['every_item']
  if (len(every_list) > 6):
    if (verb_errors): gp_warning("Warning: More than six items specified in every modifier -- additional items will be ignored.")

  # Open input datafile
  if (re.search(r"\.gz$",datafile) != None): # If filename ends in .gz, open it with gunzip
   f         = gzip.open(os.path.join(gp_settings.cwd, os.path.expanduser(datafile)),"r")
  else:
   f         = open(os.path.join(gp_settings.cwd, os.path.expanduser(datafile)),"r")
  index_no   = 0
  index_datacount = 0
  line_count = 0
  line_stepcount = 0
  block_count = 0
  block_stepcount = 0
  prev_blank = 10 # Skip opening blank lines

  fileline = 0
  try:
   for line in f: # Iterate here, don't readlines() !
    fileline = fileline + 1
    line_clean = line.strip()
    if (len(line_clean) == 0): # Ignore blank lines
      prev_blank = prev_blank + 1
      block_count += 1
      if (rows > 0):           # Make a new discontinuous line; we have a new block of data
       if ((block_stepcount < 1) and ((blockfirst == None) or (block_count >= blockfirst)) and ((blocklast == None) or (block_count <= blocklast))):
         totalgrid.append(datagrid)
         block_stepcount = blockstep-1
       else:
         block_stepcount -= 1
       line_count = 0
       line_stepcount = 0
       rows = 0
       datagrid = []
      if (prev_blank == 2): # Two blank lines means a new index
       index_no = index_no + 1
       index_datacount = 0
       block_count = 0
       block_stepcount = 0
       if ((index >= 0) and (index_no > index)): break # No more data
      continue
    if (line_clean[0] == '#'): continue # Ignore comment lines, too
    prev_blank = 0 # Reset blank lines counter

    if ((index >= 0) and (index_no != index)): continue # Still waiting for our index

    # Use only every nth datapoint, between first and last lines specified in "every" modifier
    if ((usingrowcol == "row") or 
        ((line_stepcount < 1) and ((linefirst == None) or (line_count >= linefirst)) and ((linelast == None) or (line_count <= linelast)))  ):
      # Separate line into a series of data values
      data_list = []
      for csv_item in line_clean.split(','): # First separate on commas (CSV files)
        csv_items = csv_item.split() # Then on whitespace
        if (csv_items==[]): data_list.extend(['']) # ,, means a blank data item
        else              : data_list.extend(csv_items)
      datagrid.append([[fileline for i in range(len(data_list))], index_datacount, data_list])
      rows = rows + 1
      line_stepcount = linestep - 1
    else:
      line_stepcount -= 1 # Count down counter until we take next point
    line_count     += 1
    index_datacount += 1
  except KeyboardInterrupt: raise
  except:
   if (verb_errors): gp_warning("Error encountered whilst reading datafile '%s'."%datafile)
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return [[0,0,[]]]

  f.close()
  if (rows > 0): totalgrid.append(datagrid)

  # If we have usingrowcol set to "row", we now need to rotate our provisional datagrid
  # We also filter lines (columns in the actual datafile, before rotation) as specified in the "every" modifier

  if (usingrowcol == "row"):
   outgrid  = [] # The new version of totalgrid, which we're going to build
   maxwidth = 0
   for blockgrid in totalgrid: # One data block at a time
     outblockgrid = []
     for i in range(len(blockgrid)): # Work out maximum width of datafile, to see how many lines will be in eventual datafile
       if (len(blockgrid[i][0]) > maxwidth): maxwidth = len(blockgrid[i][0])
     line_stepcount = 0
     for i in range(maxwidth): # Now fetch these lines one by one
       if ((line_stepcount < 1) and ((linefirst == None) or (i >= linefirst)) and ((linelast == None) or (i <= linelast))):
         linerow = []
         datarow = []
         for j in range(len(blockgrid)):
           if (len(blockgrid[j][0]) <= i): # We've read off the end of a short line; pad it with zeros
             linerow.append(-1)
             datarow.append("0.0")
           else:
             linerow.append(blockgrid[j][0][i]) # These are the line numbers of the datafile from which values were fetched; used in error reporting
             datarow.append(blockgrid[j][2][i]) # These are the actual data values, still in strings for the moment
         outblockgrid.append([linerow, i, datarow])
         line_stepcount = linestep - 1
       else:
         line_stepcount -= 1 # Count down counter until we take next point
     outgrid.append(outblockgrid)
   totalgrid = outgrid # Done... so ditch the old grid and replace with the new rotated version

  return grid_using_convert(totalgrid, "in datafile '%s'"%datafile, "parse data", "on line ", using_list, select_criterion, vars, funcs, style, firsterror, verb_errors)

# GRID_USING_CONVERT(): Takes a grid of data from a datafile, and applies 'using' modifier to it
# to return the output data to plot on graph

def grid_using_convert(totalgrid, description, parsedata, lineunit, using_list, select_criterion, vars, funcs, style, firsterror=None, verb_errors=False, errcount=0):
  vars_local = vars.copy()
  if (using_list == []): using_list = gp_settings.datastyleinfo[style][0].split(":")
  using_list = using_list[:]
  for i in range(len(using_list)): using_list[i] = using_list[i].strip()
  columns    = len(using_list)
  columns_using = columns
  if (columns == 1): columns = 2
  data_used  = {}
  if (firsterror == None): firsterror = gp_settings.datastyleinfo[style][2]

  try:
   # Parse using list
   for i in range(len(using_list)):
    error_str = "Internal error while parsing using expressions -- offending expression was '%s'."%using_list[i]
    # Match "23" on its own, and turn that into hidden variable _gp_param_23
    test = re.match(r"""^[0-9]*$""",using_list[i])
    if (test != None):
      number = int(test.group(0))
      data_used[number]='used'
      using_list[i] = "_gp_param"+str(number)
    else:
      # Match $23, and turn that into hidden variable _gp_param_23
      while 1:
        test = re.search(r"\$([0-9][0-9]*)",using_list[i])
        if (test != None):
          number = int(test.group(1))
          using_list[i] = using_list[i][:test.start()] + "_gp_param" + str(number) + using_list[i][test.end():]
          data_used[number]='used'
        else:
          break
      # Match $x, and turn that into hidden variable _gp_param_{x}
      while 1:
        test = re.search(r"\$([A-Za-z]\w*)",using_list[i])
        if (test != None):
          number = int(gp_eval.gp_eval(test.group(1),vars_local, funcs))
          using_list[i] = using_list[i][:test.start()] + "_gp_param" + str(number) + using_list[i][test.end():]
          data_used[number]='used'
        else:
          break
      # Match $(x), and turn that into hidden variable _gp_param_{x}
      while 1:
        test = re.search(r"\$\((.*)",using_list[i])
        if (test != None):
          brackets = gp_eval.gp_bracketmatch(test.group(1),0)
          number = int(gp_eval.gp_eval(test.group(1)[:brackets[-1]],vars_local, funcs))
          using_list[i] = using_list[i][:test.start()] + "_gp_param" + str(number) + test.group(1)[brackets[-1]+1:]
          data_used[number]='used'
        else:
          break

   # Parse select criterion
   error_str = "Internal error while parsing select criterion -- offending expression was '%s'."%select_criterion

   # Match $23, and turn that into hidden variable _gp_param_23
   while 1:
     test = re.search(r"\$([0-9][0-9]*)",select_criterion)
     if (test != None):
       number = int(test.group(1))
       select_criterion = select_criterion[:test.start()] + "_gp_param" + str(number) + select_criterion[test.end():]
       data_used[number]='used'
     else:
       break
   # Match $x, and turn that into hidden variable _gp_param_{x}
   while 1:
     test = re.search(r"\$([A-Za-z]\w*)",select_criterion)
     if (test != None):
       number = int(gp_eval.gp_eval(test.group(1),vars_local, funcs))
       select_criterion = select_criterion[:test.start()] + "_gp_param" + str(number) + select_criterion[test.end():]
       data_used[number]='used'
     else:
       break
   # Match $(x), and turn that into hidden variable _gp_param_{x}
   while 1:
     test = re.search(r"\$\((.*)",select_criterion)
     if (test != None):
       brackets = gp_eval.gp_bracketmatch(test.group(1),0)
       number = int(gp_eval.gp_eval(test.group(1)[:brackets[-1]],vars_local, funcs))
       select_criterion = select_criterion[:test.start()] + "_gp_param" + str(number) + test.group(1)[brackets[-1]+1:]
       data_used[number]='used'
     else:
       break

  except KeyboardInterrupt: raise
  except:
   if (verb_errors): gp_error(error_str)
   if (verb_errors): gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return [[0,0,[]]]

  # Check whether datafile contains only rows with one datapoint on them. If so, this is a one-column datafile, and we insert row numbers as x coordinate.
  one_column_datafile = True
  for blockgrid in totalgrid:
   for [file_lineno, index_datacount, data_list] in blockgrid:
    if (len(data_list) > 1):
     one_column_datafile = False
    if not one_column_datafile: break
   if not one_column_datafile: break

  # Now we're ready to reprocess the grid, and evaluate the given "using" expressions
  # for each dataline
  allgrid = []
  outgrid = [[]]
  for blockgrid in totalgrid:
   outblockgrid = []
   for [file_lineno, index_datacount, data_list] in blockgrid:
    fileline = file_lineno[0]
    try:
      error_str = "Warning: Could not %s %s%s %s."%(parsedata,lineunit,file_lineno[0],description)
      data_item  = []

      # For this datapoint (row of values from datafile), evaluate each of our _gp_param expressions
      # If we have only one datapoint, and are told to use 1:2, then the x-coordinate is the file line number
      invalid_datapoint = False
      if ((columns_using != 1) and one_column_datafile): # This deals with "using 1:2" when we have a one-column datafile
       for varnum,dummy in data_used.iteritems():
        error_str = "Warning: Could not %s %s%s %s."%(parsedata,lineunit,file_lineno[0],description)
        if   (varnum == 1): vars_local['_gp_param'+str(varnum)] = index_datacount # Line number is number 1
        elif (data_list[0] == ''): invalid_datapoint = True
        elif (varnum == 2): vars_local['_gp_param'+str(varnum)] = float(data_list[0]) # Value of one and only value from datafile is number 2
        else              : invalid_datapoint = True # Request for data value 3:4:5... etc
      else:
       for varnum,dummy in data_used.iteritems(): # This deals with all other datafiles (with more than one column of data in file)
         if   (varnum == 0): vars_local['_gp_param0'] = index_datacount # column zero is line numbers
         elif (varnum <= len(data_list)) and (data_list[varnum-1] != ''):
           error_str = "Warning: Could not %s %s%s %s."%(parsedata,lineunit,file_lineno[varnum-1],description)
           vars_local['_gp_param'+str(varnum)] = float(data_list[varnum-1])
         else:
           invalid_datapoint = True # Request for data value 3:4:5... etc
      if invalid_datapoint: continue

      error_str = "Warning: Could not %s %s%s %s."%(parsedata,lineunit,file_lineno[0],description)

      # Check whether this datapoint satisfies selection criteria
      if (select_criterion != ""):
       value = gp_eval.gp_eval(select_criterion, vars_local, funcs, verbose=False)
       if (value == 0.0): invalid_datapoint = True # gp_eval applies float() to result and turns False into 0.0
      if invalid_datapoint: continue

      # If only one column set in 'using', add x-coordinates from datapoint number within file index
      # e.g. 'plot using 1'
      if (columns_using == 1): data_item.append(index_datacount)

      # Now that we have values for ($1), ($2), etc... we can actually evaluate the expressions passed to us in using statement
      for i in range(len(using_list)):
        value = gp_eval.gp_eval(using_list[i], vars_local, funcs, verbose=False)
        if (not SCIPY_ABSENT) and (not scipy.isfinite(value)): raise ValueError
        if (style[-5:] != "range"):
         if ((i >= firsterror) and (value < 0.0)): # Check for negative error bars
          value = 0.0
          if (verb_errors): gp_warning("Warning: Negative errorbar detected %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
        else: # This gets executed for all kinds of error ranges ; make sure that error ranges are sensible
         if (i == 2) and (value > data_item[0]):
          value = data_item[0]
          if (verb_errors): gp_warning("Warning: x lower limit > x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
         if (i == 3) and (value < data_item[0]):
          value = data_item[0]
          if (verb_errors): gp_warning("Warning: x upper limit < x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
         if (i == 4) and (value > data_item[1]):
          value = data_item[1]
          if (verb_errors): gp_warning("Warning: y lower limit > x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
         if (i == 5) and (value < data_item[1]):
          value = data_item[1]
          if (verb_errors): gp_warning("Warning: y upper limit < y value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
        data_item.append(value)
        if (verb_errors and (errcount > ERRORS_MAX)):
         gp_warning("Warning: Not displaying any more errors for this datafile.") ; verb_errors = False
    except KeyboardInterrupt: raise
    except:
     if (verb_errors):
      if (sys.exc_info()[0] != exceptions.ValueError): gp_warning("%s %s (%s)"%(error_str,sys.exc_info()[1],sys.exc_info()[0]))
      else                                           : gp_warning("%s"%error_str)
     errcount += 1
     if (verb_errors and (errcount > ERRORS_MAX)): gp_warning("Warning: Not displaying any more errors for this datafile.") ; verb_errors = False
    else:
     # For arrow linestyles, we break up each datapoint into a line between two points
     if (style[0:6] == "arrows"): outgrid.append([2,columns,[data_item,data_item[2:4]+data_item[0:2]+data_item[4:]]]) # arrow linestyles
     else                       : outblockgrid.append(data_item)
     allgrid.append(data_item)
   if (len(outblockgrid) > 0): outgrid.append([len(outblockgrid),columns,outblockgrid])

  outgrid[0] = [len(allgrid),columns,allgrid]
  return outgrid

