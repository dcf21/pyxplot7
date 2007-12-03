# GP_PARSER.PY
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

# Parse commands, using syntax specification in gp_commands

import os
import re
import pickle

import gp_commands
import gp_eval
from gp_autocomplete import *
from gp_error import *
import gp_text
import gp_version

# --------------------------------------------------------------------------
# PART I: READ SYNTAX SPECIFICATION
#
# The syntaxes of PyXPlot commands are specified in gp_commands.
#
# We make a tree structure -- a list of lists. Each list takes the form:
#  [ [type, output_variable_name, output_variable_value, grammar_symbol] , ---- Members of structure ]
#
# type can be:
#   seq -- match each member of structure in turn
#   opt -- entire structure is optional. typically contains a seq structure.
#   rep -- repeat structure as many times as it matches input
#   per -- members of this structure may be found in any order, but each may only match once
#   ora -- match any ONE member of this structure
#
# The special type "item" has structure:
# [ ["item", match string, autocomplete level, varname, var_value] ]
#
# Only "item" and "rep" structures are allowed to return output variables "varname".
# Upon parsing a line of user input, a dictionary is returning, containing the values of all these variables.

# START_NEW_STRUCTURE(): This nests a new structure within the present structure
# def_tree is a stack, which stores are positions in structures that we are populating

def start_new_structure(type, def_tree):
  def_list_new = [[type,"","",""]] # [ type of list, output_variable_name, output_variable_value, grammar_symbol ]
  if (len(def_tree)>0):
    if (def_tree[-1][0][0] != "seq") and (type != "seq"): start_new_structure("seq", def_tree)
    def_tree[-1].append(def_list_new)
  def_tree.append(def_list_new)

# ROLL_BACK(): The opposite of the above... implements the closing bracket.
# Finishes the present structure, which should be of type "type". Throws exception if it is not.
# Note the "seq" structures are automatically closed without need for closing grammar.

def roll_back(type, def_tree, var_inputs, def_txt):
  test = re.match(r".(:([^\s]*))?\s*(.*)",def_txt) # Can have "]:foo" to store output of structure to variable foo
  assert (test != None), "Error parsing command specification:\n %s"%def_tree[0]
  varname = test.group(2)
  if (varname != None): var_inputs[varname] = None
  varset = None # For item structures we can do "exit:directive:quit" to store "quit" into variable "directive", but []s never do that.
  while (def_tree[-1][0][0] == "seq"): def_tree.pop() # Close seq structures; they don't have closing grammar
  assert (def_tree[-1][0][0] == type), "Incorrect nesting of types in command specification -- expected %s, but got %s:\n %s"%(type,def_tree[-1][0][0],def_tree[0])
  if (varname != None): def_tree[-1][0][1] = varname
  if (varset  != None): def_tree[-1][0][2] = varset
  def_tree.pop() # Close structure of type "type" and roll back stack.
  return test.group(3) # Return the unparsed remainder of the definition text string from gp_commands

# MAIN(): This code runs on startup to populate a list, "commands", with
# list-based definitions of PyXPlot's commands, parsed using the functions
# above from gp_commands

commands = []
for def_txt in gp_commands.commands.splitlines(): # Loop over PyXPlot's commands
  if (len(def_txt) == 0): continue # Ignore blank lines
  def_tree = []
  var_inputs = {}
  start_new_structure("seq",def_tree) # Each command definition is a sequence of items to be matched.
  while (def_txt != ""): # Loop over words in the gp_commands text definition
    if   (def_txt[0] == "{"): # {} grammar indicates an optional series of items, which go into a new structure.
      start_new_structure("opt",def_tree)
      def_txt = def_txt[1:].strip()
    elif (def_txt[0] == "["): # [] grammar indicates a series of items which repeat 0 or more times. These go into a new structure.
      start_new_structure("rep",def_tree)
      def_txt = def_txt[1:].strip()
    elif (def_txt[0] == "("): # () grammar indicates items which can appear in any order, but each one not more than once. New structure.
      start_new_structure("per",def_tree)
      def_txt = def_txt[1:].strip()
    elif (def_txt[0] == "<"): # <> grammar indicates a list of items of which only one should be matched. New structure.
      start_new_structure("ora",def_tree)
      def_txt = def_txt[1:].strip()
    elif (def_txt[0] == "~"): # ~ is used inside () to separate items
      while (def_tree[-1][0][0] == "seq"): def_tree.pop()
      assert (def_tree[-1][0][0] == "per"), "Tilda should be used only in permutation structures:\n %s"%def_tree[0]
      def_txt = def_txt[1:].strip()
    elif (def_txt[0] == "|"): # | is used inside <> for either/or items
      while (def_tree[-1][0][0] == "seq"): def_tree.pop()
      assert (def_tree[-1][0][0] == "ora"), "ORA should be used only in permutation structures:\n %s"%def_tree[0]
      def_txt = def_txt[1:].strip()
    elif (def_txt[0] == ">"): # Match closing brackets for the above types
      def_txt = roll_back("ora",def_tree,var_inputs,def_txt)
    elif (def_txt[0] == ")"):
      def_txt = roll_back("per",def_tree,var_inputs,def_txt)
    elif (def_txt[0] == "]"):
      def_txt = roll_back("rep",def_tree,var_inputs,def_txt)
    elif (def_txt[0] == "}"):
      def_txt = roll_back("opt",def_tree,var_inputs,def_txt)
    else:

      # This word is not grammar; it is an item to be matched
      if (def_txt[0] == "\\"): def_txt = def_txt[1:] # Escape characters put at the beginnings of words are ignored; they allow them to begin with punctuation e.g. "["
      if (def_tree[-1][0][0] != "seq"): start_new_structure("seq",def_tree) # Match words have to go in sequences, not, e.g. "ora" structures
      # General format is "foobar@3:plob:bolp". This matches foobar, autocompleting so long as 3 characters supplied.
      # and storing the value "bolp" into variable "plob". Note that "foobar" can begin with a :
      test = re.match(r"([^\s][^@:\s]*)(@([^:\s]*))?(:([^\s:]*))?(:(\S*))?\s*(.*)", def_txt)
      assert (test != None) and (test.group(8) != def_txt), "Error parsing command specification:\n %s"%def_tree[0]
      if (test.group(5) != None): var_inputs[test.group(5)] = None
      def_tree[-1].append([["item",test.group(1), test.group(3), test.group(5), test.group(7)]]) # [ "item", match string, autocomplete level, varname, var_value ]
      def_txt = test.group(8) # The unparsed remainder of the line from gp_commands

  def_tree[0][0][1] = "line" # Store whole line to "line"
  commands.append([def_tree[0],var_inputs])

# Debugging: this outputs a copy of the python syntax specification list
# for command,vardict in commands:
#  print command
#  print vardict

# --------------------------------------------------------------------------
# PART II: PARSE A LINE OF USER INPUT

# PARSE(): Top-level interface. Parses a commandline "line" from the user.
# It expects that ; and `` have already been dealt with by pyxplot.py

def parse(line, vars):
  for command,vardict in commands: # Try each command in turn to see if it fits
    match   = False # Match doesn't necessarily mean a command fully fit; it means the command began to fit, so this was the right command
    linepos = 0 # Measures how far along the line we've got
    dict    = {}
    expecting = "" # String returned in syntax error saying "these options would have been valid at this point"
    algebra_linepos = None
    algebra_error = ""
    [linepos, success, expecting, algebra_linepos, algebra_error, match, dict] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command, match, dict)
    if not match: continue # This command didn't even begin to match
    if (not success) or (line[linepos:].strip() != ""): # This command matched, but there was a syntax error along the way
      if (algebra_linepos == None): errorstr = "Syntax Error -- "
      else                        : errorstr = "At this point, was "
      if not success: # User input didn't match command specification
        errorstr += "expecting %s.\n"%expecting
      else:
        if (expecting == ""): errorstr += "unexpected trailing matter at the end of command.\n"
        else: errorstr += "expecting %s or end of command.\n"%expecting
      for i in range(linepos): errorstr += " "
      errorstr += " |\n"
      for i in range(linepos): errorstr += " "
      errorstr += "\\|/\n "+line
      if (algebra_linepos != None):
        errorstr += "\n"
        for i in range(algebra_linepos): errorstr += " "
        errorstr += "/|\\\n"
        for i in range(algebra_linepos): errorstr += " "
        errorstr += " |\n"
        errorstr += algebra_error
      gp_error("\n"+errorstr+"\n")
      return None # Return None in case of failure
    return dict # Return dictionary of variables set in parsing the command if success
  return {'directive':'unrecognised'} # We did not recognise command

# PARSE_DESCEND(): We go through command definition structure, recursively descending into sub-structures
#   line -- input line from user
#   vars -- PyXPlot's user-defined variables; used for evaluating expressions
#   linepos -- how far through line have we got with our parsing efforts so far?
#   expecting -- used to build up a list of all possible match items which could be used for next word. Used for intelligent syntax errors.
#   algebra_linepos -- if we encounter an error evaluating an expression, we store the position in the line of the error here.
#   algebra_error -- if we encounter an error evaluating an expression, we store the error message here.
#   command -- the command definition structure into which we are descending
#   match -- we set this to true when we've got match to be sure this was the command that the user wanted, even if he made a syntax error.
#   dict -- we populate this dictionary with settings from the user's input

def parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command, match, dict):
  while (linepos<len(line)) and (line[linepos] in [' ', '\t', '\n']): linepos += 1 # Fast forward over whitespace between words
  success = True # Blank structures are fit by user input

  if   (command[0][0] == "item"): # Descending into an item which we've got to match against user input
    matchlen = command[0][2]
    if (matchlen == "n"): # If match item is followed by "@n", then match whole string, but allow it to be followed by other characters
      match_string = command[0][1]
      j = linepos
      for i in range(len(command[0][1])):
        if (j < len(line)) and (line[j] == command[0][1][i]):
          j += 1
        else:
          success = False
          break
      if success: linepos = j
    else: # Match item not followed by "@n"
      if (matchlen == None): matchlen = len(command[0][1]) # If no @ modifier, we need to match whole string
      else                 : matchlen = int(matchlen)      # Otherwise, convert @ modifier to an integer value

      if (command[0][1] == "="): # = tells us that we have got far enough through syntax that this is the only command to match input
        match = True
      elif (command[0][1] == "%r"): # %r matches the rest of the line.
        match_string = line[linepos:]
        linepos = len(line)
      elif (command[0][1] == "%s"): # %s matches a single word; commas not allowed
        test = re.match(r"\s*(\w\w*)\s*(.*)", line[linepos:])
        if (test != None):
          match_string = test.group(1)
          linepos += test.start(2)
        else: success = False
      elif (command[0][1] == "%S"): # %S matches a single word; commas allowed; used to match filenames
        test = re.match(r"""\s*([^\s'"]\S*)\s*(.*)""", line[linepos:])
        if (test != None):
          match_string = test.group(1)
          linepos += test.start(2)
        else: success = False
      elif (command[0][1] == "%q"): # %q matches a quoted string
        test = re.match(r"""\s*('|")(.*)""", line[linepos:])
        if (test != None):
          quote_type = test.group(1)
          try:
            [match_string, aftermatch, quote_errpos, algebra_error] = gp_eval.gp_getquotedstring(line[linepos+test.start(1):],vars)
          except:
            algebra_linepos = linepos + test.start(1)
            algebra_error   = "Error: %s (%s)"%(sys.exc_info()[1], sys.exc_info()[0])
            success = False
          else:
            if quote_errpos!=None: algebra_linepos = linepos + test.start(1) + quote_errpos
            if (match_string != None): linepos = len(line) - len(aftermatch)
            else                     : success = False
        else: success = False
      elif (command[0][1] == "%Q"): # %Q matches the name of a string variable, and outputs it as if a quoted string
        test = re.match(r"\s*([A-Za-z]\w*)\s*(.*)", line[linepos:])
        if (test != None):
          varname = test.group(1)
          if varname in vars:
            match_string=vars[varname]
            linepos += test.start(2)
          else: success = False
        else: success = False
      elif (command[0][1] == "%a"): # %a matches an axis name, e.g. "x1"
        test = re.match(r"""\s*(x|X|y|Y|z|Z)(.*)""", line[linepos:])
        if (test != None):
          if (len(test.group(2))==0) or (test.group(2)[0]<33):
            match_string = test.group(1).lower()+"1"
            linepos += test.start(2)
          else:
            [posend, error] = gp_eval.gp_getexpression(line[linepos+test.start(2):], False)
            if (error == None):
              try:
                axis_no = int(gp_eval.gp_eval(line[linepos+test.start(2):linepos+test.start(2)+posend], vars, verbose=False))
                assert axis_no>0 and axis_no<1025, "Axis numbers should be in the range 0 --> 1024."
                match_string = test.group(1).lower() + "%d"%(axis_no)
                linepos += test.start(2)+posend
              except:
                match_string = test.group(1).lower()+"1"
                linepos += test.start(2)
            else:
              match_string = test.group(1).lower()+"1"
              linepos += test.start(2)
        else: success = False

      elif (command[0][1] == "%v"): # %v matches a variable name, e.g. "abc123"
        test = re.match(r"\s*([A-Za-z]\w*)\s*(.*)", line[linepos:])
        if (test != None):
          match_string = test.group(1)
          linepos += test.start(2)
        else: success = False

      elif (command[0][1] in ["%e","%E","%f","%d"]): # %e matches some algebra, e.g. "2*sin(x)".
        [posend, error] = gp_eval.gp_getexpression(line[linepos:], command[0][1] == "%E")
        if (error == None):
          if (command[0][1] in ["%e","%E"]): # %E is used for "plot using" expressions, where var names can start with $s
            match_string = line[linepos:linepos+posend]
            linepos += posend
          else:
            try:
              value = gp_eval.gp_eval(line[linepos:linepos+posend], vars, verbose=False)
              if   (command[0][1] == "%f"): match_string = float(value)
              elif (command[0][1] == "%d"): match_string = int(value)
              else                      : raise SyntaxError, "Should not be here!"
              linepos += posend
            except:
              algebra_linepos = linepos
              algebra_error   = "Error: %s (%s)"%(sys.exc_info()[1], sys.exc_info()[0])
              success = False 
        else:
          success = False
          if (posend > 0):
            algebra_linepos = linepos+posend
            algebra_error   = "Syntax Error -- expecting %s."%error

      else:                         # Anything else matches itself
        pos = autocomplete(line[linepos:], command[0][1], matchlen)
        if pos:
         linepos       += pos-1
         match_string   = command[0][1]
        else:   success = False

    if success: # Successful -- tell user variable about it.
      expecting = ""
      algebra_linepos = None
      algebra_error = ""
      if (command[0][3] not in [None, ""]):
        if (command[0][4] not in [None, ""]): dict[command[0][3]] = command[0][4]
        else                                : dict[command[0][3]] = match_string
    else: # Unsuccessful -- add something to "expecting" for intelligent error message
      if (len(expecting) > 0): expecting += " or "
      if (command[0][3] not in [None, ""]): varname = " ("+command[0][3]+")"
      else                                : varname = ""
      if   (command[0][1] ==  "%a"      ): expecting += "axis name"+varname                   # %a should have matched an axis name, e.g. "x1"
      elif (command[0][1] ==  "%f"      ): expecting += "numeric value or expression"+varname # %f should have matched a float expression
      elif (command[0][1] in ["%e","%E"]): expecting += "algebraic expression"+varname        # %e should have matched some algebra, e.g. "2*sin(x)"
      elif (command[0][1] ==  "%d"      ): expecting += "integer value or expression"+varname # %d should have matched an integer expression
      elif (command[0][1] ==  "%s"      ): expecting += "string"+varname            # %s should have matched a string of characters (no ,s)
      elif (command[0][1] ==  "%S"      ): expecting += "string"+varname            # %S should have matched a string of characters (,s allowed)
      elif (command[0][1] ==  "%r"      ): expecting += "string"+varname            # %r should have matched the rest of the line. It should never fail...
      elif (command[0][1] ==  "%q"      ): expecting += "quoted string"+varname     # %q should have matched a quoted string
      elif (command[0][1] ==  "%Q"      ): expecting += "variable name"+varname     # %Q should have matched a variable name (to turn into string)
      elif (command[0][1] ==  "%v"      ): expecting += "variable name"+varname     # %q should have matched a variable name
      else                               : expecting += '"'+command[0][1]+'"'       # anything else should have matched itself

    while (linepos<len(line)) and (line[linepos] in [' ', '\t', '\n']): linepos += 1 # Fast forward over whitespace between words

  elif (command[0][0] == "seq"): # Descending into a sequence of items which we've got to match one by one
    for i in range(1,len(command)):
      [linepos, success, expecting, algebra_linepos, algebra_error, match, dict] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command[i], match, dict)
      if not success: break

  elif (command[0][0] == "rep"): # Descending into a repeating item which we can match 0 or more times
    repeating = True
    dict_baby_list = [] # Output from repeating item is a list of dictionaries, one from each repeat
    first = True
    while repeating:
      dict_baby = {}
      linepos_old = linepos
      if (command[0][1][-1] in [":",","]) and (not first):
        [linepos, success, expecting, algebra_linepos, algebra_error, match, dict_baby] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, [["item",command[0][1][-1],"n",None,None]], match, dict_baby) # Match link character between repeats
      first = False
      if success:
        for i in range(1,len(command)):
          [linepos, success, expecting, algebra_linepos, algebra_error, match, dict_baby] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command[i], match, dict_baby) # Try to repeat
          if not success:
            if (linepos == linepos_old): success = True # If we haven't actually processed any characters in trying to repeat, that's fine
            repeating = False # But we can't stop part-way through a repeat
            break
      else:
        repeating = False
        success = True # If we don't get repeat character, we just don't repeat
      if repeating: dict_baby_list.append(dict_baby) # If that repeat was successful, append baby dictionary to list of dictionaries
    dict[ command[0][1] ] = dict_baby_list # Store list of dictionaries in user variable

  elif (command[0][0] == "opt"): # Descending into an optional item
    linepos_old = linepos
    for i in range(1,len(command)):
      [linepos, success, expecting, algebra_linepos, algebra_error, match, dict] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command[i], match, dict)
      if not success:
        if (linepos == linepos_old): success = True # If we fail, doesn't matter, this was optional. But we mustn't have matched ANYTHING
        break

  elif (command[0][0] == "per"): # Descending into a permutation item -- items from this list can appear in any order
    repeating = True
    excluded  = []
    while repeating:
      linepos_old = linepos
      for i in range(1,len(command)):
        if not i in excluded:
          [linepos, success, expecting, algebra_linepos, algebra_error, match, dict] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command[i], match, dict)
        else:
          success = False
        if success:
          excluded.append(i) # Can only have one copy of each possible item
          break
        else:
          if (linepos != linepos_old): break # An item began to match, but couldn't finish.
      if not success:
        repeating = False
        if (linepos == linepos_old): success = True

  elif (command[0][0] == "ora"): # Descending into a either / or item
    linepos_old = linepos
    for i in range(1,len(command)):
      [linepos, success, expecting, algebra_linepos, algebra_error, match, dict] = parse_descend(line, vars, linepos, expecting, algebra_linepos, algebra_error, command[i], match, dict)
      if success: break
      if (linepos != linepos_old): break # An OR item began to match, but couldn't finish. This is a slight fudge. Basically, OR items must differ in first word.
  else:
    raise SyntaxError, "command parsing error:\n%s"%command # This is an internal error
  return [linepos, success, expecting, algebra_linepos, algebra_error, match, dict]
