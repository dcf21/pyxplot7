# GP_FIT.PY
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
import gp_datafile
from gp_autocomplete import *
from gp_error import *

import sys
import re
from math import *

try:
 import scipy
 from scipy.optimize import fmin
 from scipy import linalg
except: SCIPY_ABSENT = True
else: SCIPY_ABSENT = False

pass_function = ''
no_arguments  = 0
len_vialist   = 0
pass_vialist  = []
pass_vars     = {}
pass_funcs    = {}
pass_dataset  = []
x_bestfit     = []

yerrors = 0

# FIT_RESIDUAL(): Evaluates the residual between function and dataset

#         x = List of values of via parameters
#      yerr = If True, then errorbars are contained in the n+1 th column of
#             pass_dataset. If False then not.
# yerr_subs = The error bar to assume in the event that data does not have
#             errorbars given.

# The best fitting via parameters are actually independent of the magnitude of
# error bars if all datapoints have a common error, and so the value of
# yerr_subs will not affect the best fit values found, but *does* affect the
# Hessian matrix and consequently the uncertainty in the best fit parameters
# found. Consequently, it is used in hessian_get() above.

def fit_residual(x, yerr=None, yerr_subs=1.0):
  global pass_function, no_arguments, pass_range, pass_vialist, pass_xname, pass_vars, pass_funcs, pass_dataset
  global yerrors

  if (yerr == None): yerr = yerrors

  local_vars  = pass_vars
  for i in range(len(pass_vialist)): # Set via variable values
    local_vars[pass_vialist[i]] = x[i]

  accumulator = 0.0 # Add up sum of square residuals
  for datapoint in pass_dataset:
    eval_string = pass_function+"("
    for i in range(no_arguments):
      eval_string += str(datapoint[i])
      if (i != (no_arguments-1)): eval_string += ","
    eval_string += ")"
    residual    = datapoint[no_arguments] - gp_eval.gp_eval(eval_string,local_vars,pass_funcs)
    if yerr:
      residual = residual / (sqrt(2)*datapoint[no_arguments+1]) # If yerr=True, divide each residual by (sqrt(2)*sigma)
    else:
      residual = residual / (sqrt(2)*yerr_subs                ) # If yerr=False, substitute yerr_subs for standard error
    accumulator = accumulator + pow(residual, 2.0)

  return accumulator # This is the negative of the log probability distribution over x

# HESSIAN_GET(): Function for evaluating the hessian matrix of the probability
# distribution of the via parameters

# x_bestfit = List of values of best fitting via parameters.
#      yerr = If True, then errorbars are contained in the n+1 th column of
#             pass_dataset. If False then not.
# yerr_subs = The error bar to assume in the event that data does not have
#             errorbars given.
#       i,j = The desired component of the Hessian matrix.

def hessian_get(x_bestfit, yerr, yerr_subs, i, j):
  epsilon_i = max(1e-50, abs(x_bestfit[i]*1e-6)) # Stepsize to use in numerical differentiation
  epsilon_j = max(1e-50, abs(x_bestfit[j]*1e-6))
  x_local   = x_bestfit.copy()
  d2L       = 0.0

  # What follows is numerical second differentiation, to find d2L / d[x_i]d[x_j]

  x_local[i] += epsilon_i/2 ; x_local[j] += epsilon_j/2 ; d2L += fit_residual(x_local, yerr, yerr_subs)
  x_local[i] -= epsilon_i                               ; d2L -= fit_residual(x_local, yerr, yerr_subs)
  x_local[j] -= epsilon_j                               ; d2L += fit_residual(x_local, yerr, yerr_subs)
  x_local[i] += epsilon_i                               ; d2L -= fit_residual(x_local, yerr, yerr_subs)
  d2L = d2L / epsilon_i / epsilon_j
  return -d2L # Take negative here because fit_residual returns negative of log P

# SIGMA_LOGP(): This function is minimised whilst we are searching for the
# optimum uncertainty in the supplied data. Effectively, we are trying to
# maximise P(sigma_data) = P(datafile|sigma)*P(sigma) = Evidence*Prior. This is
# marginalised over all of the parameters which we've fitted to the data.
#
# As integrating over all our fitted parameters is computationally intensive,
# we approximate this (see MacKay, D.J.C.M., Neural Computation, 4, 415-447
# (1992)) as P(sigma_data) = P(datafile|x,sigma) * Occam Factor, where the left
# term is the likelihood for the best fit case.
#
# It can be shown that the Occam Factor is proportional to one over the square
# root of the determinant of the Hessian matrix.

def sigma_logP(sigma):
  global x_bestfit, len_vialist, pass_dataset

  assert not SCIPY_ABSENT, "The fit command requires the scipy module for python, which is not installed. Please install and try again."

  if (sigma[0] < 0.0): return float('nan') # Negative errorbars are silly

  # Term1 is the likelihood for the best-fit parameters, without Gaussian normalisation factor
  term1   = -fit_residual(x_bestfit, False, sigma[0])

  # Term2 is the Gaussian normalisation factor
  term2   =  len(pass_dataset) * log( 1.0 / (sqrt(2*pi)*sigma[0]))

  # Term3 is the Occam Factor
  hessian =  scipy.mat([[hessian_get(x_bestfit, yerrors, sigma[0], i, j) for i in range(len_vialist)] for j in range(len_vialist)])
  hessian_det = linalg.det(-hessian)
  assert (hessian_det>=0.0), "Negative Hessian Matrix has negative determinant. This implies negative error bars. The fitting procedure has probably failed."
  term3   =  log(1/sqrt(hessian_det))

  return -(term1+term2+term3) # Proportional to negative of log probability of sigma

# DIRECTIVE_FIT(): Implements the "fit" directive

def directive_fit(command, vars, funcs):
  global pass_function, no_arguments, len_vialist, pass_vialist, pass_vars, pass_funcs, pass_dataset
  global yerrors, x_bestfit

  assert not SCIPY_ABSENT, "The fit command requires the scipy module for python, which is not installed. Please install and try again."

  # FIRST OF ALL, READ THE INPUT PARAMETERS FROM THE COMMANDLINE

  # Ranges
  ranges = []
  for drange in command['range_list']:
   if 'min' in drange.keys(): range_min = drange['min']
   else                     : range_min = None
   if 'max' in drange.keys(): range_max = drange['max']
   else                     : range_max = None
   ranges.append([ range_min , range_max ])

  # Function name
  pass_function = command['fit_function']
  if not pass_function in funcs: gp_error("Error: fit command requested to fit function '%s'; no such function."%pass_function) ; return
  no_arguments  = funcs[pass_function][0]

  # Read datafile filename
  datafile = command['filename']

  # every
  if 'every_list:' in command: every = command['every_list:']
  else                       : every = []

  # index
  if 'index' in command: index = int(command['index'])
  else                 : index = -1 # default

  # select
  if 'select_criterion' in command: select_criteria = command['select_criterion']
  else                            : select_criteria = ''

  # smooth
  if 'smooth' in command: smoothing = float(command['smooth'])
  else                  : smoothing = 0.0

  # Using rows or columns
  if   'use_rows'    in command: usingrowcol = "row"
  elif 'use_columns' in command: usingrowcol = "col"
  else                         : usingrowcol = "col" # default

  # using
  if 'using_list:' in command: using = [item['using_item'] for item in command['using_list:']]
  else                       : using = [str(i+1) for i in range(no_arguments+1)]

  # via
  vialist = [item['fit_variable'] for item in command['fit_variables,']]
  
  # We have now read all of our commandline parameters, and are ready to start fitting
  try:
    (rows,columns,datagrid) = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, every, vars, funcs, "points", firsterror=no_arguments+1)[0]
    datagrid_cpy = []
    for datapoint in datagrid:
     if False not in [(i>=columns) or (((ranges[i][0] == None) or (datapoint[i]>ranges[i][0])) and ((ranges[i][1] == None) or (datapoint[i]<ranges[i][1]))) for i in range(len(ranges)) ]:
      datagrid_cpy.append(datapoint)
    datagrid = datagrid_cpy
  except KeyboardInterrupt: raise
  except:
    gp_error("Error reading input datafile:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  if   (columns <  (no_arguments+1)):
    gp_error("Error: fit command needs %d columns of input data to fit a %d-parameter function."%(no_arguments+1,no_arguments))
    return # Error
  elif (columns == (no_arguments+1)): yerrors = False
  elif (columns == (no_arguments+2)): yerrors = True
  else:
   yerrors = True
   gp_warning("Warning: Too many columns supplied to fit command. Taking 1=first argument, .... , %d=%s(...), %d=errorbar on function output."%(no_arguments+1,pass_function,no_arguments+2))

  pass_vialist = vialist
  len_vialist  = len(vialist)
  pass_vars    = vars.copy()
  pass_funcs   = funcs
  pass_dataset = datagrid

  # Set up a list containing the values of all of the parameters that we're fitting
  x = []
  for i in range(len_vialist):
    if vialist[i] in pass_vars: x.append(pass_vars[vialist[i]]) # Use default value, if we have one
    else                      : x.append(1.0                  ) # otherwise use 1.0 as our starting value

  # Find best fitting parameter values
  try:
    x = fmin(fit_residual, x, disp=0)
    x_bestfit = x
  except KeyboardInterrupt: raise
  except:
    gp_error("Numerical Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  # Print best fitting parameter values
  try:
    gp_report("\n# Best fit parameters were:")
    gp_report(  "# -------------------------\n")
    for i in range(len_vialist): # Set via variables
      gp_report("%s = %s"%(vialist[i],x[i]))
      vars[vialist[i]] = x[i] # Set variables in global scope
  except KeyboardInterrupt: raise
  except:
    gp_error("Error whilst display best fit values:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  # Estimate error magnitude in supplied data, if not supplied (this is critical to error in fitted paramters).
  gp_report("\n# Estimated error in supplied data values (based upon misfit to this function fit, assuming uniform error on all datapoints):")
  if not yerrors:
    try:
     sigma_data = fmin(sigma_logP, [1.0], disp=0)
     gp_report(  "sigma_datafile = %s\n"%sigma_data)
    except KeyboardInterrupt: raise
    except:
      gp_error("Error whilst estimating the uncertainties in parameter values.\nError:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
      sigma_data = 1.0
      # Keep going; we may as well print out the Hessian matrix anyway
  else:
    gp_report("# Not calculated, because datafile already contained errorbars on data values.\n")
    sigma_data = 0.0 # sigma_data is the errorbar on the supplied datapoints

  # Calculate and print the Hessian matrix
  try:
    hessian = scipy.mat([[hessian_get(x, yerrors, sigma_data, i, j) for i in range(len_vialist)] for j in range(len_vialist)])
    matrix_print(hessian, vialist, "Hessian matrix of log-probability distribution", "hessian")

    hessian_negative = True
    for i in range(len_vialist):
     for j in range(len_vialist):
      if (hessian[i,j] > 0.0): hessian_negative = False
    if not hessian_negative: gp_warning("\n# *** WARNING: ***\n# Non-negative components in Hessian matrix. This implies that fitting procedure has failed.\n")
  except KeyboardInterrupt: raise
  except:
    gp_error("Error whilst evaluating Hessian matrix.\nError:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  # Print the Covariance matrix
  try:
    covar = linalg.inv(-hessian) # Covariance matrix = inverse(-H)
    matrix_print(covar, vialist, "Covariance matrix of probability distribution", "covariance")
  except KeyboardInterrupt: raise
  except:
    gp_error("Error whilst evaluating covariance matrix.\nError:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  # Get the standard errors on each parameter, which are the squareroots of the leading diagonal terms
  try:
    standard_devs = []
    for i in range(len_vialist):
      assert (covar[i,i] >= 0.0), "Negative terms in leading diagonal of covariance matrix imply negative variances in fitted parameters. The fitting procedure has probably failed."
      standard_devs += [sqrt(covar[i,i])]
  except KeyboardInterrupt: raise
  except:
    gp_error("Error whilst evaluating uncertainties in best fit parameter values.\nError:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  # Print the Correlation matrix
  try:
    for i in range(len_vialist):
     for j in range(len_vialist):
      covar[i,j] = covar[i,j] / standard_devs[i] / standard_devs[j]
    matrix_print(covar, vialist, "Correlation matrix of probability distribution", "correlation")
  except KeyboardInterrupt: raise
  except:
    gp_error("Error whilst evaluating correlation matrix.\nError:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  # Print the standard errors on variables
  try:
    gp_report("\n# Uncertainties in best fit parameter values are:")
    gp_report(  "# -----------------------------------------------\n")
    for i in range(len_vialist):
      gp_report("sigma_%s = %s"%(vialist[i],standard_devs[i]))

    # Print final summary
    gp_report("\n# Summary:")
    gp_report(  "# --------\n#")
    for i in range(len_vialist):
      gp_report("# %s = %s +/- %s"%(vialist[i],x[i],standard_devs[i]))
  except KeyboardInterrupt: raise
  except:
    gp_error("Error whilst displaying uncertainties in best fit parameter values.\nError:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return # Error

  return # Done!!!

# MATRIX_PRINT(): Display a matrix, using the strings from vialist as column/row headings

def matrix_print(matrix, vialist, longtitle, shorttitle):

  # Print title at top of matrix
  gp_report("\n# %s is:\n# %s\n"%(longtitle, ''.join(['-' for i in range(4+len(longtitle))])))

  # Print list of column headings along the top
  line = "# %6s%3s   "%("","")
  for j in range(len(vialist)): line += "%6s%s "%(vialist[j][:5],['   ','...'][len(vialist[j])>5])
  gp_report(line)

  # Now print each row of the matrix
  for i in range(len(vialist)):
   line = "# %6s%s ( "%(vialist[i][:5],['   ','...'][len(vialist[i])>5]) # Row headings
   for j in range(len(vialist)):
    line += "%9.2e "%matrix[i,j]
   gp_report(line+" )")

  # Now print again in machine-readable format
  gp_report("\n# %s matrix in Python-readable format:\n# ----------------------------------%s\n\n%s = %s\n"%(shorttitle.capitalize(), ''.join(['-' for i in range(len(shorttitle))]), shorttitle, [[matrix[i,j] for j in range(len(vialist))] for i in range(len(vialist))]))
 
