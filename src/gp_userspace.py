# GP_USERSPACE.PY
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

import math
import re

try: import scipy.integrate
except: SCIPY_ABSENT = True
else: SCIPY_ABSENT = False

import gp_spline
import gp_eval

# Math functions which we allow user to use
math_functions={"acos":math.acos,
"asin":math.asin,
"atan":math.atan,
"atan2":math.atan2,
"ceil":math.ceil,
"cos":math.cos,
"cosh":math.cosh,
"degrees":math.degrees,
"exp":math.exp,
"fabs":math.fabs,
"floor":math.floor,
"fmod":math.fmod,
"frexp":math.frexp,
"hypot":math.hypot,
"ldexp":math.ldexp,
"log":math.log,
"log10":math.log10,
"max":max,
"min":min,
"modf":math.modf,
"pow":math.pow,
"radians":math.radians,
"sin":math.sin,
"sinh":math.sinh,
"sqrt":math.sqrt,
"tan":math.tan,
"tanh":math.tanh,
}

variables  = {'pi':3.14159265358979}       # User-defined variables
functions  = {}                            # Verbal description of user-defined functions
function_namespace = math_functions.copy() # Python namespace for functions which we allow user to use

# MAKE_FUNCTION_LAMBDA_WRAPPER():
def make_function_lambda_wrapper(name):
 exec("""expression_lambda = lambda *x: function_wrapper('%s',x)"""%name)
 return expression_lambda

# GP_FUNCTION_DECLARE(): Declare a new function, possibly with a range
def gp_function_declare(line):
 test = re.match(r'([A-Za-z]\w*)\(([^()]*)\)\s*([^=]*)=(.*)',line.strip())
 assert (test != None), "Error: bad function definition '%s' could not be parsed."%line

 name       = test.group(1) # The name of the function
 arguments  = gp_eval.gp_split(test.group(2),",") # A textual list of its arguments
 arguments2 = [] # A stripped and checked list of its arguments
 ranges     = gp_eval.gp_split(test.group(3),"[")[1:] # List of range strings
 ranges2    = [] # A stripped and checked list of range strings
 expression = test.group(4).strip()

 assert name not in math_functions.keys(), "Cannot re-define a core mathematical function."
 if name in variables: del variables[name]

 expression_lambda = make_function_lambda_wrapper(name)

 for argument in arguments:
  test2 = re.match(r'^[A-Za-z]\w*$',argument.strip())
  assert (test2 != None), "Error: Function has badly formed argument name '%s'."%argument
  arguments2.append(argument.strip())

 for i in range(len(arguments)):
  if (i >= len(ranges)):
   ranges2.append([None, None]) # No range, if none specified
  else:
   rangestr = ranges[i].strip()
   if (rangestr == "]"): # Case [] means all x
    min = max = None
   else:
    test2 = re.match("([^:\]]*)((:)|( *to *))([^:\]]*)\]", rangestr)
    if (test2 == None): raise SyntaxError, "Error: range of argument %d should take form [min:max] or [min to max], but instead has form '[%s'."%(i+1,rangestr)
    min = test2.group(1).strip()
    max = test2.group(5).strip()
    if (len(min) == 0): min = None
    if (len(max) == 0): max = None
   ranges2.append([min,max])

 if   (len(expression) == 0)                                  :
  if name in functions:
   del functions[name]
   del function_namespace[name]
 else:
   function_namespace[name]=expression_lambda
   if not ((name in functions) and (functions[name]['no_args']==len(arguments)) and (functions[name]['type']=='function')):
     functions[name] = {'no_args':len(arguments), 'type':'function', 'histogram':False, 'filename':None, 'defn':[]}
   functions[name]['defn'].append({'args':arguments2,'ranges':ranges2,'expr':expression})
   print function_namespace

# GP_VARIABLE_SET(): Declare a new user-defined variable
def gp_variable_set(name,value):
 name=name.strip()
 assert name not in math_functions.keys(), "Cannot re-define a core mathematical function."
 if name in functions:
   del functions[name]
   del function_namespace[name]
 variables[name]=value

def gp_variable_del(name)      :
 name=name.strip()
 assert name not in math_functions.keys(), "Cannot re-define a core mathematical function."
 if name in functions:
  del functions[name]
  del function_namespace[name]
 if name in variables:
  del variables[name]

# GP_VARIABLE_RE(): Apply a regular expression to a string variable
def gp_variable_re(name,regex):
 name=name.strip()
 assert name in variables, "No such variable: %s"%name
 assert len(regex)>0, "Expecting regular expression to follow."
 split_char=regex[0]
 words=regex.split(split_char)
 assert len(words)==4, "Regular expression should have the form s/search/replace/flags."
 assert words[3]=="", "Regular expression flags are not yet implemented."
 variables[name] = re.sub(words[1],words[2],str(variables[name]))

# passed_to_funcwrap -- Passed from gp_eval; variables which are defined in the current scope, for function wrapper to access

passed_to_funcwrap = {'vars':{},'iter':0,'verbose':False}

# FUNCTION_WRAPPER(): Wrapper for user-defined function evaluation
def function_wrapper(name, params):
 fexp = functions[name]
 if (len(params) != fexp['no_args']): raise SyntaxError, "Function '%s' takes %d arguments; %d provided."%(name,fexp['no_args'],len(params))
 if (fexp['type']=='spline'): # This is a spline
  try:
   return gp_spline.spline_evaluate(params[0], fexp['splineobj'])
  except KeyboardInterrupt: raise
  except:
   raise ValueError, "Error evaluating spline %s"%name
 else:             # This is a function
  for defno in range(len(fexp['defn'])):
   j = len(fexp['defn']) - 1 - defno
   func_scope = passed_to_funcwrap['vars'].copy()
   inrange = True
   for i in range(fexp['no_args']): func_scope[fexp['defn'][j]['args'][i]] = params[i]
   for i in range(fexp['no_args']):
    if inrange:
     try:
      if (fexp['defn'][j]['ranges'][i][0] != None): minrange = gp_eval.gp_eval(fexp['defn'][j]['ranges'][i][0],func_scope,False,passed_to_funcwrap['iter']+1)
      else                                        : minrange = None
      if (fexp['defn'][j]['ranges'][i][1] != None): maxrange = gp_eval.gp_eval(fexp['defn'][j]['ranges'][i][1],func_scope,False,passed_to_funcwrap['iter']+1)
      else                                        : maxrange = None
     except KeyboardInterrupt: raise
     except:
      if passed_to_funcwrap['verbose']:
       gp_error("Error evaluating range of function '%s'."%name)
       gp_error("(it may be necessary to delete it with 'f(x)=' and then redefine it)")
      raise
     if ((minrange != None) and (params[i] < minrange)): inrange = False
     if ((maxrange != None) and (params[i] > maxrange)): inrange = False
   if inrange: return gp_eval.gp_eval(fexp['defn'][j]['expr'],func_scope,False,passed_to_funcwrap['iter']+1)
  raise ValueError, "Attempt to evaluate function '%s' with arguments out of their specified ranges."%func

# GP_EVAL_INTEGRAND(): Evaluates an integrand, passed to it from the scipy.integrate.quad function
# def gp_eval_integrand(x, expression, xname, vars, iteration):
#  vars[xname] = x
#  return gp_eval(expression, vars, False, iteration+1)
#
#    # Evaluate any integral functions
#    while 1:
#      test = re.match(r"(.*(^|\W))int_d([A-Za-z]\w*)\((.*)$",expression)
#      if (test == None): break
#      assert not SCIPY_ABSENT, "The integration of functions requires the scipy module for python, which is not installed. Please install and try again."
#      func = test.group(3)
#      bracketmatch = gp_bracketmatch(expression, test.start(4)-1)
#      if (len(bracketmatch) == 0): raise SyntaxError, "Mismatched brackets for integral 'int_d%s'."%func
#      if (len(bracketmatch) != 3): raise SyntaxError, "Integral 'int_d%s' should take three parameters -- expression, min, max."%func
#      min = gp_eval(expression[ (bracketmatch[0]+1):bracketmatch[0+1] ], vars, funcs, False, iteration+1)
#      max = gp_eval(expression[ (bracketmatch[1]+1):bracketmatch[1+1] ], vars, funcs, False, iteration+1)
#      func_scope = vars.copy()
#      integration_result = scipy.integrate.quad(gp_eval_integrand, min, max, full_output=1, args=(expression[test.start(4):bracketmatch[0]],func,func_scope,funcs,iteration))
#      if verbose and (len(integration_result)>3):
#        gp_warning("Warning whilst integrating expression %s:\n%s"%(expression[test.start(4):bracketmatch[0]],integration_result[3]))
#      expression = test.group(1) + str(integration_result[0]) + expression[bracketmatch[len(bracketmatch)-1]+1:]
#
#    # Evaluate any differential function
#    while 1:
#      test = re.match(r"(.*(^|\W))diff_d([A-Za-z]\w*)\((.*)$",expression)
#      if (test == None): break
#      func = test.group(3)
#      bracketmatch = gp_bracketmatch(expression, test.start(4)-1)
#      if   (len(bracketmatch) == 0):
#        raise SyntaxError, "Mismatched brackets for differential 'diff_d%s'."%func
#      elif (len(bracketmatch) == 2):
#        epsilon1 = epsilon2 = 1e-6
#      elif (len(bracketmatch) == 3):
#        epsilon1 = gp_eval(expression[ (bracketmatch[1]+1):bracketmatch[1+1] ], vars, funcs, False, iteration+1)
#        epsilon2 = 1e-6
#      elif (len(bracketmatch) == 4):
#        epsilon1 = gp_eval(expression[ (bracketmatch[1]+1):bracketmatch[1+1] ], vars, funcs, False, iteration+1)
#        epsilon2 = gp_eval(expression[ (bracketmatch[2]+1):bracketmatch[2+1] ], vars, funcs, False, iteration+1)
#      else:
#        raise SyntaxError, "Differential 'diff_d%s' should take 2-4 parameters -- expression, point at which to differentiate, epsilon."%func
#      func_scope = vars.copy()
#      xval = gp_eval(expression[ (bracketmatch[0]+1):bracketmatch[0+1] ], vars, funcs, False, iteration+1)
#      epsilon = epsilon1 + xval * epsilon2
#      func_scope[func] = xval-epsilon/2.0 ; x1 = gp_eval(expression[ test.start(4):bracketmatch[0]], func_scope, funcs, False, iteration+1)
#      func_scope[func] = xval+epsilon/2.0 ; x2 = gp_eval(expression[ test.start(4):bracketmatch[0]], func_scope, funcs, False, iteration+1)
#      expression = test.group(1) + str((x2-x1)/epsilon) + expression[bracketmatch[len(bracketmatch)-1]+1:]
#
#
#    # Evaluate any functions
#    for func,fexp in funcs.iteritems():
#      while 1:
#        test = re.match(r"(.*(^|\W))%s\s*\((.*)$"%func,expression)
#        if (test == None): break
#        bracketmatch = gp_bracketmatch(expression, test.start(3)-1)
#        if (len(bracketmatch) == 0):            raise SyntaxError, "Mismatched brackets for function '%s'."%func
#        if (len(bracketmatch) != abs(fexp[0])): raise SyntaxError, "Function '%s' takes %d arguments; %d provided."%(func,abs(fexp[0]),len(bracketmatch))
#        args = []
#        bracketmatch.insert(0,test.start(3)-1)
#        for i in range(abs(fexp[0])):
#          args.append(gp_eval(expression[ (bracketmatch[i]+1):bracketmatch[i+1] ], vars, funcs, False, iteration+1))
#        if (fexp[0] < 0): # This is a spline
#          try:
#            value = gp_spline.spline_evaluate(args[0], fexp[1][0][1])
#            expression = test.group(1) + str(value) + expression[bracketmatch[len(bracketmatch)-1]+1:]
#          except KeyboardInterrupt: raise
#          except:
#            raise ValueError, "Error evaluating spline %s"%func
#        else:             # This is a function
#          funcdone = False
#          for defno in range(len(fexp[1])):
#            if not funcdone:
#              j = len(fexp[1]) - 1 - defno
#              func_scope = vars.copy()
#              inrange = True
#              for i in range(fexp[0]): func_scope[fexp[1][j][0][i]] = args[i]
#              for i in range(fexp[0]):
#                try:
#                 if (fexp[1][j][1][i][0] != None): minrange = gp_eval(fexp[1][j][1][i][0],func_scope,funcs,False,iteration+1)
#                 else                            : minrange = None
#                 if (fexp[1][j][1][i][1] != None): maxrange = gp_eval(fexp[1][j][1][i][1],func_scope,funcs,False,iteration+1)
#                 else                            : maxrange = None
#                except KeyboardInterrupt: raise
#                except:
#                 if (verbose):
#                  gp_error("Error evaluating range of function '%s'."%func)
#                  gp_error("(it may be necessary to delete it with 'f(x)=' and then redefine it)")
#                 raise
#                if ((minrange != None) and (args[i] < minrange)): inrange = False
#                if ((maxrange != None) and (args[i] > maxrange)): inrange = False
#              if inrange:
#                expression = test.group(1) + str(gp_eval(fexp[1][j][2],func_scope,funcs,False,iteration+1)) + expression[bracketmatch[len(bracketmatch)-1]+1:]
#                funcdone   = True
#          if not funcdone:
#            raise ValueError, "Attempt to evaluate function '%s' with arguments out of their specified ranges."%func
#
#
