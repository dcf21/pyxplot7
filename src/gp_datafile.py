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

from math import sqrt, pi

import os
import sys
import re
import gzip

try: import scipy
except: SCIPY_ABSENT = True
else: SCIPY_ABSENT = False

ERRORS_MAX = 4

# GP_DATAREAD(): Read a data file, selecting only every nth item from index m, using ....
#                This is just a wrapper for make_datagrid

def gp_dataread(datafile, index, usingrowcol, using_list, select_criterion, select_cont, every_list, vars, style, verb_errors=True, firsterror=None):
  # Open input datafile; if filename ends in .gz, open it with gunzip
  if (re.search(r"\.gz$",datafile) != None): f = gzip.open(os.path.join(gp_settings.cwd, os.path.expanduser(datafile)),"r") 
  elif datafile=="-"                       : f = sys.stdin
  else                                     : f = open(os.path.join(gp_settings.cwd, os.path.expanduser(datafile)),"r")

  datagrid = make_datagrid(iterate_file(f), "of file %s"%datafile, "line ", index, usingrowcol, using_list, select_criterion, select_cont, every_list, vars, style, verb_errors, firsterror=None)

  if f!=sys.stdin: f.close()
  return datagrid

# GP_FUNCTION_DATAGRID(): Evaluate a (set of) function(s), producing a grid of values
# This mostly wraps make_datagrid with a bit of cleverness
def gp_function_datagrid(xrast, functions, xname, usingrowcol, using_list, select_criterion, select_cont, every_list, vars, style, verb_errors=True, firsterror=None):
  datagrid   = []
  local_vars = vars.copy()

  # Construct a description string
  if (len(functions)==1):
   description = "in function %s"%functions[0]
  else:
   description = "in functions %s"%', '.join(functions)

  # Obtain the set of functions
  datagrid = make_datagrid(iterate_function(xrast, functions, xname, local_vars), description, "x=", 0, usingrowcol, using_list, select_criterion, select_cont, every_list, local_vars, style, verb_errors, firsterror)

  # If function evaluation produced no data we check for unevaluable functions.
  # Alternatively there may have been a bad select criterion (in which case the
  # user will already have warnings) or an overly restrictive select criterion
  # (in which case it's their fault anyway and might even be what they wanted).
  if (len(datagrid) == 1): 
   local_vars[xname] = xrast[0]
   for item in functions:
    try:
     val = gp_eval.gp_eval(item,local_vars,verbose=False)
    except KeyboardInterrupt: raise
    except:
     if verb_errors: gp_error("Error evaluating expression '%s':"%item)
     raise
   # If there *was* no select criterion then there is a bug here
   if (select_criterion == ''):
    gp_warning("Warning: Evaluation of %s produced no data!"%(description[3:],select_criterion))
   elif (verb_errors):
    gp_warning("Warning: Evaluation of %s with select criterion %s produced no data!"%(description[3:],select_criterion))
    
  return datagrid

# ITERATE_FUNCTION(): Given a function description iterate it over a supplied raster

def iterate_function(xrast, functions, xname, vars):
  local_vars = vars.copy()
  for x in xrast:
   local_vars[xname] = x
   datapoint = [x]
   for item in functions:
    try:    val = gp_eval.gp_eval(item,local_vars,verbose=False)
    except KeyboardInterrupt: raise
    except: datapoint.append('Function evaluation failure') # This string value will trigger a subsequent error
    else:   datapoint.append(val)
   yield [datapoint, x]

# ITERATE_FILE(): iterate over a file, returning the lines as lists of floats

def iterate_file(f):
   Nline = 0 # File line number
   for line in f:
    Nline += 1
    if (line[0] == '#'): continue # Ignore comment lines
    line_clean = line.strip()
    # Separate line into a series of data values
    data_list = []
    for csv_item in line_clean.split(','): # First separate on commas (CSV files)
     csv_items = csv_item.split() # Then on whitespace
     if (csv_items==[]): data_list.extend(['']) # ,, means a blank data item
     else              : data_list.extend(csv_items)
     data_list.extend(csv_items)
    yield [data_list, Nline]

# MAKE_DATAGRID(): Make a big grid of data to be plotted given an iterator that
# produces lines of data.  The function used to form most of gp_dataread
#
# make_datagrid works in three steps:
# Step 1 -- parse the using, every and select modifiers to work out exactly what data we want
#           We then set up a structure called data_required, into which we will put that data
#           We design this structure cunningly so that we can tell from it which data to retrieve
# 
# Step 2 -- We read in the file / iterate through the function and obtain that data
# 
# Step 3 -- We evaluate the using and select statements for each data point and build up a grid of data to return

def make_datagrid(iterator, description, lineunit, index, usingrowcol, using_list, select_criterion, select_cont, every_list, vars, style, verb_errors=True, firsterror=None):
  index_no   = 0
  rows       = 0
  single_column_datafile = True  # This will be falsified later should the datafile be multi-column
  single_row_datafile = True

  # Step 1. -- Work out what bits of data we want

  # Check for blank using list and replace with default, remembering that we did so
  if (using_list == []): 
   using_list = gp_settings.datastyleinfo[style][0].split(":")
   fudged_using_list = True
  else:
   fudged_using_list = False

  # Tidy stuff up and set default arrays
  using_list = using_list[:] # This is funky python shit
  for i in range(len(using_list)): using_list[i] = using_list[i].strip()
  columns    = len(using_list)
  columns_using = columns # The number of columns of data specified in the "using" statement
  if (columns == 1): columns=2 # The number of columns of data that we return.  If the user has only specified a single column we give them the row index too.
  # datagrid   = []
  totalgrid  = [] # List of [file linenumber, line number for spare x-axis, list of data strings]s for all of the blocks that we're going to plot
  vars_local = vars.copy()
  data_used = {}
  errcount = 0

  # Parse the "every" list
  # XXX fix this to return the dict directly XXX
  [linestep,blockstep,linefirst,blockfirst,linelast,blocklast] = parse_every(every_list, verb_errors)
  if (linestep == None): linestep = 1
  if (linefirst == None): linefirst = 0
  if (blockstep == None): blockstep = 1
  if (blockfirst == None): blockfirst = 0
  every_dict = {"linestep":linestep, "blockstep":blockstep, "linefirst":linefirst, "blockfirst":blockfirst, "linelast":linelast, "blocklast":blocklast}

  try:
   # Parse using list
   error_str = 'Internal error while parsing using expressions'
   parse_using (using_list, data_used, vars_local, verb_errors)

   # Check for the case where the using list doesn't specify any variables
   if (data_used == {}):
    data_used[0] = "used" # We need a single set of data anyway so that we get the right number of points; think about p sin(x) u (1)

   # Parse select criterion
   error_str = "Internal error while parsing select criterion -- offending expression was '%s'."%select_criterion
   select_criterion = parse_select (select_criterion, data_used, vars_local)

  except KeyboardInterrupt: raise
  except:
   if (verb_errors): gp_error(error_str)
   if (verb_errors): gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return [[0,0,[]]]

  # Work out what data we need from the file
  data_required = {'rows':{'data':{}, 'lineNs':[{}]},
                   'cols':{'data':{}, 'lineNs':[[]]}}
  # OK, listen up.  The data structure now looks like this:
  # 'data' -> dictionary of col/row numbers, -> list of blocks -> list of points
  # 'lineNs' -> list of blocks -> (rows) dictionary of row # / line # pairs
  #                               (cols) list of blocks -> list of line #s
  # The point of doing it like this is that we can do rows and cols in the same loop
  rowcol = "%ss"%usingrowcol
  if (usingrowcol == "row"):
   # Rename for convenience
   # For each row that we need, create a dictionary in the database to hold it
   for row,dummy in data_used.iteritems():
    data_required['rows']['data'][row] = []
  else: 
   # For each column that we need, create a dictionary in the database to hold it
   for col,dummy in data_used.iteritems():
    data_required['cols']['data'][col] = [[]] # Include a blank list to put the first block of data into

  # Step 2 -- Get the required data from the file
  
  line_count = 0
  block_count = 0 # This counts blocks within an index block
  Nblocks = 0     # Count total number of blocks
  prev_blank = 10 # Skip opening blank lines 

  fileline = 0
  try:
   for line in iterator: # Iterate here, don't readlines() !
    fileline = line[1]
    data_list = line[0]
    # Check for a blank line; if found update block and index accounting as necessary
    if (len(data_list) == 0):
      prev_blank += 1
      block_count += 1
      if (rows > 0): # Discontinuous line; we have a new block of data
       Nblocks += 1
       for col in data_required['cols']['data']:
        data_required['cols']['data'][col].append([])
       # If no matching row has been found for any given row in this block then we insert a dud row
       # XXX Think about line numbers XXX
       for row in data_required['rows']['data']:
        if len(data_required['rows']['data'][row]) < Nblocks:
         data_required['rows']['data'][row].append([])
       if (rowcol == 'cols'):
        data_required['cols']['lineNs'].append([])
       else:
        data_required['rows']['lineNs'].append({})

       line_count = 0
       rows = 0
      if (prev_blank == 2): # Two blank lines means a new index
       index_no = index_no + 1
       block_count = 0
       if ((index >= 0) and (index_no > index)): break # No more data
      continue
    prev_blank = 0 # Reset blank lines counter

    if ((index >= 0) and (index_no != index)): continue # Still waiting for our index

    # This is the line number within the current block
    line_count += 1

    # See if the data matches a requested row
    for row in data_required['rows']['data']:
     if (row == line_count):
      if (row != 1): 
       single_row_datafile = False
      # Check each data point against the every statement
      filtered_data_list = []
      for i in range(len(data_list)):
       if (check_every(block_count, i, every_dict)):
        filtered_data_list.append(data_list[i])
      # Note that if filtered_data_list is blank at this point we correctly append a blank list
      data_required['rows']['data'][row].append(filtered_data_list)
      data_required['rows']['lineNs'][Nblocks][row] = fileline
      continue # no row can match more than one row number

    # Or a requested column
    # First check against criteria from "every" statement
    if (usingrowcol == 'col'):
     if (check_every(block_count, line_count-1, every_dict)):
      if len(data_list)>1: single_column_datafile = False
      for col in data_required['cols']['data']:
       myblock = len(data_required['cols']['data'][col]) - 1 # Data block to write to
       if (col <= len(data_list)):
        data_required['cols']['data'][col][myblock].append(data_list[col-1])
       else:
        data_required['cols']['data'][col][myblock].append('')
      data_required['cols']['lineNs'][myblock].append(fileline)

    rows += 1
   # Check that the last set of rows was complete
   for row in data_required['rows']['data']:
    if len(data_required['rows']['data'][row]) < Nblocks+1:
     data_required['rows']['data'][row].append([])
     data_required['rows']['lineNs'][Nblocks][row] = -1

  except KeyboardInterrupt: raise
  except:
   if (verb_errors): gp_warning("Error encountered whilst reading '%s'."%description)
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return [[0,0,[]]]

  # Step 3 -- Get the set of data that we want from the data extracted from the file

  if (firsterror == None): firsterror = gp_settings.datastyleinfo[style][2]
  allgrid = []
  outgrid = [[]]

  # Deal with the special case where the user didn't supply a using list and the file only has one column/row
  if (fudged_using_list):
   if (single_column_datafile and usingrowcol == "col"):
    # In this case we want to just plot the first column against the data item counter.
    using_list = ['1']
    parse_using (using_list, data_used, vars_local, verb_errors)
    del data_required['cols']['data'][2]
    columns_using = 1
   elif (single_row_datafile and usingrowcol == "row"):
    # Ditto but for the first row
    using_list = ['1']
    parse_using (using_list, data_used, vars_local, verb_errors)
    del data_required['rows']['data'][2]
    columns_using = 1

  # In the following, "rc" means "row or column, as appropriate"
  data_rcs = data_required[rowcol]['data'].keys()  # The list of rcs that we require
  # Pick the first rc as an example for iterating over etc.
  a_rc = data_rcs[0]
  Nblocks = len(data_required[rowcol]['data'][a_rc]) # The number of blocks of data extracted from the file

  # Assemble the blocks of data to return one by one
  for i in range(Nblocks):
   data_counter = 0
   outblockgrid = []
   # If some rcs have more data in than others, then find the rc with the minimum number of points in; that is the number that we return
   # This is only ever an issue for rows, not columns, where it's dealt with when reading in the data (you can't do that for rows without double-passing)
   Npoints = len(data_required[rowcol]['data'][a_rc][i])
   for rc in data_rcs:
    Npoints = min(Npoints, len(data_required[rowcol]['data'][rc][i]))

   # Iterate over the points in this block
   for j in range(Npoints):
    data_item = []
    invalid_datapoint = False

    # Get line number / x co-ordinate / whatever for error message purposes
    if (lineunit != "line " and data_required[rowcol]['data'].has_key(1)): linenumber = data_required[rowcol]['data'][1][i][j]  # Extract the x value of the point, not the line number
    elif (rowcol == 'cols'): linenumber = "%d"%data_required['cols']['lineNs'][i][j] # Just one line number in the columns case
    else: linenumber = ''.join(["%d, "%data_required['rows']['lineNs'][i][k] for k in data_rcs])

    # For each row / column that we need, place its value in the relevent _gp_param variable
    for rc in data_rcs:
     if (rc == 0):
      vars_local['_gp_param0'] = data_counter
     else:
      point = data_required[rowcol]['data'][rc][i][j]
      if point == '':  # Lack of a data point; silently ignore
       invalid_datapoint = True
       break
      else:
       try:
        vars_local['_gp_param'+str(rc)] = float(point)
       except: # Error float()ing the data point
        invalid_datapoint = True
        if (verb_errors): 
         gp_warning("Warning: Could not evaluate data at %s%s %s."%(lineunit, linenumber, description))
         errcount += 1
         if (errcount > ERRORS_MAX): gp_warning("Warning: Not displaying any more errors for %s."%description) ; verb_errors = False
        break
    if invalid_datapoint: continue

    try: # To evaluate this data point
     # Check whether this data point satisfies select() criteria
     if (select_criterion != ""):
      error_str = "Warning: Could not evaluate select criterion at %s%s %s."%(lineunit, linenumber, description)
      if (gp_eval.gp_eval(select_criterion, vars_local, verbose=False) == 0.0): 
       invalid_datapoint = True # gp_eval applies float() to result and turns False into 0.0
       if ((select_cont == False)and(len(outblockgrid) > 0)): # Break line by creating new block here if the user has asked for discontinuous breaking with select
        outgrid.append([len(outblockgrid), columns, outblockgrid])
        outblockgrid = []
       continue

     # Evaluate the using statement
     if (columns_using == 1): data_item.append(data_counter) # If the user asked for a single column, prepend the point number
     data_counter += 1

     error_str = "Warning: Could not parse data at %s%s %s."%(lineunit, linenumber, description)
     errcount += evaluate_using(data_item, using_list, vars_local, style, firsterror, verb_errors, lineunit, linenumber, description)
     if (verb_errors and (errcount > ERRORS_MAX)):
      gp_warning("Warning: Not displaying any more errors for %s."%description) 
      verb_errors = False

    except KeyboardInterrupt: raise
    except ValueError:
     if (verb_errors):
      gp_warning("%s"%error_str)
      errcount += 1
      if (verb_errors and (errcount > ERRORS_MAX)): gp_warning("Warning: Not displaying any more errors for %s."%description) ; verb_errors = False
    except:
     if (verb_errors):
      gp_warning("%s %s (%s)"%(error_str,sys.exc_info()[1],sys.exc_info()[0]))
      errcount += 1
      if (verb_errors and (errcount > ERRORS_MAX)): gp_warning("Warning: Not displaying any more errors for %s."%description) ; verb_errors = False
    else:
     # For arrow linestyles, we break up each datapoint into a line between two points
     if (style[0:6] == "arrows"): outgrid.append([2,columns,[data_item,data_item[2:4]+data_item[0:2]+data_item[4:]]]) # arrow linestyles
     else                       : outblockgrid.append(data_item) # Append this data item to the current block
     allgrid.append(data_item) # Append the data item to the list of all data items (all the blocks catenated)
   if (len(outblockgrid) > 0): outgrid.append([len(outblockgrid),columns,outblockgrid])

  outgrid[0] = [len(allgrid),columns,allgrid]
  return outgrid

# EVALUATE_USING(): Evaluates the using() statement for a single data point
def evaluate_using(data_item, using_list, vars_local, style, firsterror, verb_errors, lineunit, fileline, description):
  errcount = 0
  for k in range(len(using_list)):
   value = gp_eval.gp_eval(using_list[k], vars_local, verbose=False)
   if (not SCIPY_ABSENT) and (not scipy.isfinite(value)): raise ValueError
   if (style[-5:] != "range"):
    if ((firsterror != None) and (k >= firsterror) and (value < 0.0)): # Check for negative error bars
     value = 0.0
     if (verb_errors): gp_warning("Warning: Negative errorbar detected %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
   elif (style[0] == "y"): # yerrorbar styles... first quoted error is y-error
     if (k == 2) and (value > data_item[1]):
      value = data_item[1]
      if (verb_errors): gp_warning("Warning: y lower limit > x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
     if (k == 3) and (value < data_item[1]):
      value = data_item[1]
      if (verb_errors): gp_warning("Warning: y upper limit < x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
   else: # This gets executed for all kinds of error ranges ; make sure that error ranges are sensible
    if (k == 2) and (value > data_item[0]):
     value = data_item[0]
     if (verb_errors): gp_warning("Warning: x lower limit > x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
    if (k == 3) and (value < data_item[0]):
     value = data_item[0]
     if (verb_errors): gp_warning("Warning: x upper limit < x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
    if (k == 4) and (value > data_item[1]):
     value = data_item[1]
     if (verb_errors): gp_warning("Warning: y lower limit > x value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
    if (k == 5) and (value < data_item[1]):
     value = data_item[1]
     if (verb_errors): gp_warning("Warning: y upper limit < y value %s%s %s."%(lineunit,fileline,description)) ; errcount+=1
   data_item.append(value)
  return errcount
   
# PARSE_EVERY: Parse an "every" modifier, returning the linestep, blockstep...

def parse_every (every_list, verb_errors):
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
  return [linestep,blockstep,linefirst,blockfirst,linelast,blocklast]

# PARSE_USING: Parse a "using" modifier, modifying to provide references to the relevent local variables

def parse_using (using_list, data_used, vars_local, verb_errors):
  for i in range(len(using_list)):
   error_str = "Internal error while parsing using expressions -- offending expression was '%s'."%using_list[i]
   # Match "23" on its own, and turn that into hidden variable _gp_param23
   test = re.match(r"""^[0-9]*$""",using_list[i])
   if (test != None):
     number = int(test.group(0))
     data_used[number]='used'
     using_list[i] = "_gp_param"+str(number)
   else:
     # Match $23, and turn that into hidden variable _gp_param23
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
         number = int(gp_eval.gp_eval(test.group(1),vars_local))
         using_list[i] = using_list[i][:test.start()] + "_gp_param" + str(number) + using_list[i][test.end():]
         data_used[number]='used'
       else:
         break
     # Match $(x), and turn that into hidden variable _gp_param_{x}
     while 1:
       test = re.search(r"\$\((.*)",using_list[i])
       if (test != None):
         brackets = gp_eval.gp_bracketmatch(test.group(1),0)
         number = int(gp_eval.gp_eval(test.group(1)[:brackets[-1]],vars_local))
         using_list[i] = using_list[i][:test.start()] + "_gp_param" + str(number) + test.group(1)[brackets[-1]+1:]
         data_used[number]='used'
       else:
         break
  return

# PARSE_SELECT: Parse a "select" modifier, modifying to provide references to the relevent local variables

def parse_select (select_criterion, data_used, vars_local):
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
      number = int(gp_eval.gp_eval(test.group(1),vars_local))
      select_criterion = select_criterion[:test.start()] + "_gp_param" + str(number) + select_criterion[test.end():]
      data_used[number]='used'
    else:
      break
  # Match $(x), and turn that into hidden variable _gp_param_{x}
  while 1:
    test = re.search(r"\$\((.*)",select_criterion)
    if (test != None):
      brackets = gp_eval.gp_bracketmatch(test.group(1),0)
      number = int(gp_eval.gp_eval(test.group(1)[:brackets[-1]],vars_local))
      select_criterion = select_criterion[:test.start()] + "_gp_param" + str(number) + test.group(1)[brackets[-1]+1:]
      data_used[number]='used'
    else:
      break
  return select_criterion

def check_every (block, line, every_dict):
  if (block < every_dict['blockfirst']): 
   return False
  if (every_dict['blocklast'] != None and block > every_dict['blocklast']):
   return False
  if (line < every_dict['linefirst']):
   return False
  if (every_dict['linelast'] != None and line > every_dict['linelast']):
   return False
  if (every_dict['blockstep'] > 1 and (block-every_dict['blockfirst'])%every_dict['blockstep'] != 0):
   return False
  if (every_dict['linestep'] > 1 and (line-every_dict['linefirst'])%every_dict['linestep'] != 0):
   return False
  return True
