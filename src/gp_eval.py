# GP_EVAL.PY
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

# Evaluates expressions using user variables and functions

import sys
import re

from gp_error import *
import gp_userspace

# GP_EVAL(): Evaluates an expression, substituting user defined variables and functions
def gp_eval(expression, vars, verbose=True, iteration=1):
  if (iteration > 20):
   raise OverflowError, "Iteration depth exceeded in function evaluation."
  try:
    # Quick escape route if we're just evaluating a variable name
    if expression in vars: return vars[expression]
    # And also for really simple numbers
    try: evalexp = float(expression)
    except: pass
    else: return evalexp

    gp_userspace.passed_to_funcwrap = {'vars':vars,'iter':iteration,'verbose':verbose}
    return float(eval(expression, gp_userspace.function_namespace.copy(), vars))
  except KeyboardInterrupt: raise
  except:
   if (verbose):
    gp_error("Error evaluating expression %s"%expression)
    gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   raise

# GP_BRACKETMATCH(): Find a matching closing bracket for an opening bracket

def gp_bracketmatch(expression, i):
  # Returns a list of comma positions in expression
  # Final item on list is closing )

  bracket_level = 0
  max           = len(expression)
  list          = []

  while( i < max-1 ):
    i = i+1 # Start searching after bracket at position i
    if (expression[i]==')'):
      if (bracket_level == 0):
        list.append(i)
        return list
      else:
        bracket_level = bracket_level - 1
    elif (expression[i]=='('):
        bracket_level = bracket_level + 1
    elif (expression[i]==','):
      if (bracket_level == 0):
        list.append(i)
        continue

# GP_GETQUOTEDSTRING(): Extract a quoted string, finding the end of the string.
# The first character of the passed string is expected to be ('|"). Escaped
# quote characters, \' and \" are unescaped and ignored in the output.

def gp_getquotedstring(string):
  quotetype = string[0]
  if (not quotetype in ["'", '"']): raise SyntaxError, "'Quoted' string does not start with quote character."

  stringend = None
  for i in range(1, len(string)):
    if (string[i] == quotetype) and (string[i-1] != '\\'):
     stringend = i
     break
  if (stringend == None): return [None, None]
  text = string[1:i]
  aftertext = string [i+1:]
  text = re.sub(r"\\'", "'", text)
  text = re.sub(r'\\"', '"', text)
  return [text, aftertext]

# GP_SPLIT(): An intelligent string splitter, which doesn't grab split
# characters embedded in () or ""

def gp_split(expression, splitchar):
  bracket_level = 0
  quote_level   = 0
  apostro_level = 0
  max           = len(expression)
  list          = []
  i             = -1
  word          = ""

  while( i < max-1 ):
    i = i+1
    if   ((expression[i]==')') and (apostro_level == 0) and (quote_level   == 0)): bracket_level = bracket_level - 1
    elif ((expression[i]=='(') and (apostro_level == 0) and (quote_level   == 0)): bracket_level = bracket_level + 1 
    elif ((expression[i]=='"') and (apostro_level == 0)): quote_level   = 1 - quote_level   # Hyphens allowed in quotes and vice-versa
    elif ((expression[i]=="'") and (quote_level   == 0)): apostro_level = 1 - apostro_level
    elif (expression[i]==splitchar):
      if ((bracket_level == 0) and (quote_level == 0) and (apostro_level == 0)):
        list.append(word)
        word=""
        continue
    word = word + expression[i]
  list.append(word)
  return list

# We've hit the end of string without brackets being closed
  return ()

# GP_GETEXPRESSION(): Extracts the longest possible valid algebraic expression
# from the beginning of a string.

# Go through string, spotting atoms from the following list:

# S -- the beginning of the string
# E -- the end of the expression
# B -- a bracketed () series of characters
# D -- a dollar sign -- only allowed in using expressions in the plot command as special variable name
# M -- a minus sign before a numeric value, variable name, or ()
# N -- a numerical value, e.g. 1.2e-34
# O -- an operator, + - * ** / % << >> & | ^ < > <= >= == != <>
# V -- a variable name

# S can be followed by  BDMN V not by E    O
# E
# B can be followed by E    O  not by  BDMN V
# D can be followed by  B  N V not by E DM O
# M can be followed by  BD N V not by E  M O
# N can be followed by E    O  not by  BDMN V
# O can be followed by  BDMN V not by E    O
# V can be followed by EB   O  not by   DMN V

# Returns [ position in string of end of expression, "expecting" error string ]

def gp_getexpression(string, dollar_allowed=False):
  state = "S" # At the beginning
  allowed_next = {"S":["B","D","M","N",    "V"    ],
                  "B":[                "O",    "E"],
                  "D":["B",        "N",    "V"    ],
                  "N":[                "O",    "E"],
                  "M":["B","D","M","N",    "V"    ],
                  "O":["B","D","M","N",    "V"    ],
                  "V":["B",            "O",    "E"]
                  }
  linepos = 0
  while (state != "E"):
   expecting = []
   for type in allowed_next[state]:
     s = string[linepos:]

     if   (type == "E"):
      state = "E" # If we're allowed to end here, and we've got to the end of the allowed_next list, the end we have reached
      expecting = []
      break # We've matched an atom (E)

     elif (type == "B"):
      test = re.match("\s*(\(.*)",s)
      if (test != None):
       bracket_match = gp_bracketmatch(string, linepos+test.start(1))
       if (bracket_match != None):
        linepos = bracket_match[-1]+1 # +1 because we want character after ")"
        state = "B"
        expecting = []
        break # We've matched an atom (B)
       else:
        return [linepos+test.start(1), "a closing bracket to match this one"]
      expecting.append('"("')

     elif (type == "D"):
      if dollar_allowed:
       test = re.match(r"\s*\$(.*)",s)
       if (test != None):
        linepos += test.start(1)
        expecting = []
        break # We've matched an atom (D)
       expecting.append("""$""")

     elif (type == "M"):
      test = re.match("\s*((-)|(not))\s*(.*)",s)
      if (test != None):
       linepos += test.start(4)
       expecting = []
       break # We've matched an atom (M)
      expecting.append("""a minus sign""")

     elif (type == "N"):
      test = re.match(r"\s*[+-]?(\d*)\.?(\d*)([eE][+-]?\d\d*)?\s*(.*)",s)
      if (test != None) and (len(test.group(1))+len(test.group(2)) > 0):
       linepos += test.start(4)
       state = "N"
       expecting = []
       break # We've matched an atom (N)
      expecting.append("a numeric value")

     elif (type == "O"):
      test = re.match(r"\s*((and)|(or)|(<=)|(>=)|(==)|(!=)|(<>)|(<<)|(>>)|(\*\*)|\+|-|\*|/|%|&|\||\^|<|>)\s*(.*)",s)
      if (test != None):
       linepos += test.start(12)
       state = "O"
       expecting = []
       break # We've matched an atom (O)
      expecting.append("""an operator (i.e. +  -  *  **  /  %  <<  >>  &  |  ^  <  >  <=  >=  ==  !=  "and" "or" or  <> )""")

     elif (type == "V"):
      test = re.match(r"\s*[A-Za-z]\w*\s*(.*)",s)
      if (test != None):
       linepos += test.start(1)
       state = "V"
       expecting = []
       break # We've matched an atom (V)
      expecting.append("""a variable or function name""")

     else:
      raise SyntaxError, "Internal Error; shouldn't get here!"

   if (expecting != []): break

  if (state == "E"):
    return [linepos, None]
  else:
    expect_str = ""
    for x in expecting:
      if (expect_str != ""): expect_str += " or "
      expect_str += x
    return [linepos, expect_str]
