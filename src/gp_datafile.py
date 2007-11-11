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
   if (verb_errors):
    if (select_criterion == ''): gp_warning("Warning: Evaluation of %s produced no data!"%(description[3:]))
    else                       : gp_warning("Warning: Evaluation of %s with select criterion %s produced no data!"%(description[3:],select_criterion))
    
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
    yield [data_list, Nline]

# MAKE_DATAGRID(): Make a big grid of data to be plotted given an iterator that
# produces lines of data.  The function used to form most of gp_dataread
#
# make_datagrid works in three steps:
# Step 1 -- parse the using, every and select modifiers to work out exactly what data we want
#           We then set up a structure called data_from_file, into which we will put that data
#           We design this structure cunningly so that we can tell from it which data to retrieve
# 
# Step 2 -- We read in the file / iterate through the function and obtain that data
# 
# Step 3 -- We evaluate the using and select statements for each data point and build up a grid of data to return

def make_datagrid(iterator, description, lineunit, index, usingrowcol, using_list, select_criterion, select_cont, every_list, vars, style, verb_errors=True, firsterror=None):
  # Note that from henceforth, "rc" means "row or column, as appropriate"
  index_no   = 0
  single_rc_datafile = True  # This will be falsified later should the datafile be multi-column/row (as appropriate)

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
  totalgrid  = [] # List of [file linenumber, line number for spare x-axis, list of data strings]s for all of the blocks that we're going to plot
  vars_local = vars.copy()
  data_used = {}
  errcount = 0

  # Parse the "every" list
  every_dict = parse_every(every_list, verb_errors)

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

  data_from_file = {'data':{}, 'lineNs':[{}]  }
  # OK, listen up.  We only ever need rows *or* columns.  So combine the two into one data structure, which looks like this:
  # data_from_file = { 'data'  : { <1st rc> : [ [ point 1, point 2, ...]  <-- values for the 1st row/column in the first block
  #                                             [ point 1, point 2, ...]  <-- "----------------------------------" second block
  #                                             [ .....................] ],
  #                                <2nd rc> : [ [ point 1, point 2, ...]   <-- values for the 2nd row/column in the first block
  #                                             [ point 1, point 2, ...]   <-- values for the 2nd row/column in the 2nd block
  #                                             [...                   ] ],
  #                                ... }
  #                    'lineNs': [  { <row/point 1> : <line N>, <row/point 2> : <line N> ...},   <-- Line numbers for the first block
  #                                 { <row/point 1> : <line N>, <row/point 2> : <line N> ...},   <-- Line numbers for the second block
  #                                                           ]
  # The part about data makes reasonable sense: data is stored by rc number first, then block by block as it comes in.  This is easiest from the readin POV.
  # 
  # Line numbers need a tad more explaining.  For ROWS, the line number of each ROW   must be stored within each block.  Each POINT then comes from the same row.
  #                                           For COLS, the line number of each POINT must be stored within each block.  Each COL   then comes from the same row.
  for rc, dummy in data_used.iteritems():
   data_from_file['data'][rc] = [[]]   # Include a blank list to put the first block of data into

  # Step 2 -- Get the required data from the file
  
  line_count = 0  # Count lines within a block
  block_count = 0 # Count blocks within an index block
  Nblocks = 0     # Count total number of blocks
  prev_blank = 10 # Skip opening blank lines 
  fileline = 0    # The line number within the file that the bit of data that we're looking at came from

  try:
   for line in iterator: # Iterate here, don't readlines() !
    fileline = line[1]
    data_list = line[0]

    # Check for a blank line; if found update block and index accounting as necessary
    if (data_list == ['']):
     prev_blank += 1
     block_count += 1
     if (line_count > 0): # Discontinuous line; we have a new block of data
      Nblocks += 1
      if (usingrowcol == "row") :
       for row in data_from_file['data']:
       # Fill in any rows that we didn't get with blank rows (though this data will be useless anyway)
        if len(data_from_file['data'][row]) < Nblocks:
         data_from_file['data'][row].append([])
       # Create blank lists to put the next block#'s worth of rows in
        data_from_file['data'][row].append([])
      else:
       # Create blank lists to put the next block#'s worth of rows in
       for col in data_from_file['data']:
        data_from_file['data'][col].append([])
      data_from_file['lineNs'].append({})

      line_count = 0
     if (prev_blank == 2): # Two blank lines means a new index
      index_no += 1
      block_count = 0
      if ((index >= 0) and (index_no > index)): break # No more data
     continue
    else: prev_blank = 0 # Reset blank lines counter

    if ((index >= 0) and (index_no != index)): continue # Still waiting for our index block; we don't want this line of data

    # This is the line number within the current block
    line_count += 1

    if usingrowcol == 'row':
     # See if data matches a requested row
     for row in data_from_file['data']:
      if (row == line_count):
       if (row != 1): single_rc_datafile = False
       # Check each data point against the 'every' statemetn
       for i in range(len(data_list)):
        if (check_every(block_count, i, every_dict)): data_from_file['data'][row][Nblocks].append(data_list[i]) # Insert into the already present blank list
       data_from_file['lineNs'][Nblocks][row] = fileline
       continue # Any given row can only match one row number
      
    else:
     # See if data matches a required column
     if check_every(block_count, line_count-1, every_dict):
      cols_read = len(data_list) # Number of cols we read from the file
      if cols_read > 1: single_rc_datafile = False
      for col in data_from_file['data']:
       if (col <= cols_read): data_from_file['data'][col][Nblocks].append(data_list[col-1]) # We have read the col that we're looking for; insert datum
       else                 : data_from_file['data'][col][Nblocks].append('') # We have not read the col that we're looking for; insert blank item
      data_from_file['lineNs'][Nblocks][len(data_from_file['data'][col][Nblocks])-1] = fileline # The last index is the item number in the data array
     
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
  if (fudged_using_list and single_rc_datafile):
    # In this case we want to just plot the first rc against the data item counter.
    using_list = ['1']
    parse_using (using_list, data_used, vars_local, verb_errors)
    del data_from_file['data'][2]
    columns_using = 1

  data_rcs = data_from_file['data'].keys()  # The list of rcs that we require

  # Nblocks should be the number of blocks (currently it is the index of the last block)
  Nblocks += 1
  
  # Assemble the blocks of data to return one by one
  for i in range(Nblocks):
   data_counter = 0
   outblockgrid = []
   # If some rcs have more data than others, then find the rc with the minimum number of points; we return that number of points
   # This is only ever an issue for rows, not columns, where it's dealt with when reading in the data (you can't do that for rows without double-passing)
   Npoints = min([len(data_from_file['data'][rc][i]) for rc in data_rcs])

   # Iterate over the points in this block
   for j in range(Npoints):
    data_item = []
    invalid_datapoint = False

    # Get line number / x co-ordinate / whatever for error message purposes
    if (lineunit != "line " and data_from_file['data'].has_key(1)): linenumber = data_from_file['data'][1][i][j]  # Extract the x value of the point, not the line number
    elif (usingrowcol == 'col'): linenumber = "%d"%data_from_file['lineNs'][i][j] # Just one line number in the columns case
    else: linenumber = ''.join(["%d, "%data_from_file['lineNs'][i][k] for k in data_rcs])

    # For each row / column that we need, place its value in the relevent _gp_param variable
    for rc in data_rcs:
     if (rc == 0):
      vars_local['_gp_param0'] = data_counter
     else:
      point = data_from_file['data'][rc][i][j]
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
  # Practical re-interpretation of "None"
  if (linestep == None): linestep = 1
  if (linefirst == None): linefirst = 0
  if (blockstep == None): blockstep = 1
  if (blockfirst == None): blockfirst = 0
  return {"linestep":linestep, "blockstep":blockstep, "linefirst":linefirst, "blockfirst":blockfirst, "linelast":linelast, "blocklast":blocklast}

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
