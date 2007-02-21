# GP_MATH.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
#
# $Id: gp_math.py,v 1.21 2007/02/21 03:48:00 dcf21 Exp $
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

# Mathematical tools used in pyxplot

from gp_error import *
import math

# Work out maximum range of floating point arithmetic on this system

EXP_MAX = 1 ; dummy = 0
try:
 while (dummy != 1e1000000):
  EXP_MAX = EXP_MAX + 1
  dummy = float("1e%d"%EXP_MAX)
except OverflowError: pass
EXP_MAX = EXP_MAX-2             # EXP_MAX is the largest floating point exponent that we can cope with
FLT_MAX = float("1e%d"%EXP_MAX) # FLT_MAX is the largest floating point number that we can cope with

# RASTER MAKING FUNCTIONS

# LINRAST()
# LOGRAST(): Linear and log rasters, used for evaluating functions

def linrast( xmin, xmax, steps):
    return [ xmin + i* float(xmax-xmin)/steps for i in range(steps+1) ]
    
def lograst ( xmin , xmax , nsteps):
    if (xmin <= 0.0):
     gp_warning("Warning: Minimum end of logarithmic axis range is trying to expand to negative ordinates. Setting new minimum for axis range to 1e-6.")
     xmin = 1e-6
    if (xmax <= 0.0):
     gp_warning("Warning: Maximum end of logarithmic axis range is trying to expand to negative ordinates. Setting new maximum for axis range to 1.0.")
     xmax = 1.0
    return [ xmin * (xmax / xmin ) ** ( float(i)/nsteps ) for i in range(nsteps+1) ]

# MIN / MAX -- Return the largest / smallest of two numbers
# Used for working out range of axes which may possibly be inverted

def min(first, second):
 if ((first == None) or (second == None) or (first < second)): return first
 return second

def max(first, second):
 if ((first == None) or (second == None) or (first < second)): return second
 return first

# ISEQUAL(): Test if two floating point numbers of are equal. Equivalent to ==
# operator, but allows for numeric errors in floating point numbers to given
# tolerance.

def isequal(a,b,tol=1e-14):
 diff = math.fabs(a-b)
 mag  = max(math.fabs(a),math.fabs(b))
 try:
  if ((diff/mag) > tol): return False
  else                 : return True
 except:
  return True

def islessthan(a,b,tol=1e-14):
 return (a<b) and not isequal(a,b,tol)

def isgreaterthan(a,b,tol=1e-14):
 return (a>b) and not isequal(a,b,tol)

# ISINTEGER(): Test whether a value is an integer or not

def isinteger(x,tol=1e-14):
 return isequal(x, math.floor(x+0.5),tol)

# VAL2STRING(): Convert a numeric value to a string. Only include decimal places if not an integer.

def val2string(x):
 if isinteger(x): return "%d"%int(math.floor(x+0.5))
 else           : return "%s"%x

# SGN(): Returns the sign of a float

def sgn(x):
 if (x < 0.0): return -1.0
 else        : return 1.0

# GETMANTISSA() and GETEXPONENT(): Functions for doing a mantissa/exponent
# decomposition of a number in any given base.

def getexponent(x,base=10.0):
 return math.floor(math.log(x,base))

def getmantissa(x, base=10.0):
 exponent = math.floor(math.log(x,base))
 return x/math.pow(base,exponent)

# FACTORISE(): Returns a list of the factors of a number

def factorise(x):
 factors = []
 for i in range(1,int(x/2+1)):
  if (x%i == 0): factors.append(i)
 return factors

sort_on_first_list_item = lambda a,b: int(sgn(a[0]-b[0]))
