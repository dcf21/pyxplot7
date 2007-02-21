# GP_HELP.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
#
# $Id: gp_help.py,v 1.12 2007/02/21 03:48:00 dcf21 Exp $
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

import os
import sys
import re
import xml.dom.pulldom

import gp_version
from gp_error import *
from gp_autocomplete import *

try: import curses
except: pass

width=0
addspace = True

# WORDWRAP_ADDWORD()

def wordwrap_addword(line, word):
  global width,addspace
  if (word == r"\\"): # \\ indicates hard new-line
    addspace = False
    return line+"\n"
  else:
    output  = line
    if addspace: output += ' \n'[(len(line)-line.rfind('\n')-1 + len(word) >= width)]
    output += word
    addspace = True
    return output

# WORDWRAP_DISPLAY(): Displays text word-wrapped for current terminal width

def wordwrap_display(input, interactive):
  global width,addspace

  # Special control codes used to produce < and >
  input = re.sub(r'\\lab', '<', input)
  input = re.sub(r'\\rab', '>', input)
  input = re.sub(r'\$VERSION', gp_version.VERSION, input)
  input = re.sub(r'\$DATE', gp_version.DATE, input)

  if (sys.stdin.isatty() and interactive):
    try:
      curses.setupterm()
      width = curses.tigetnum('cols')
      if (width > 80): width = 80 # Wider text gets a bit unreadable
    except KeyboardInterrupt: raise
    except:
      gp_warning("Warning: cannot establish the width of the current terminal.")
      width = 80
  else:
      width = 80
  paragraphs = input.strip().split("\n\n")
  text_out = ""
  for paragraph in paragraphs:
    words = paragraph.strip().split()
    if (len(words) > 0):
      addspace = True
      text_out += reduce(wordwrap_addword, words )+"\n\n"

  # Display help
  text_out = re.sub('#',' ',text_out) # Hash sign is used as a hard space
  if (sys.stdin.isatty() and interactive):
    f = os.popen("less","w")
    f.write(text_out)
    f.close()
  else:
    gp_report(text_out)
  return

# DIRECTIVE_HELP(): Implementation of the help command

def directive_help(command, interactive):

  help_words = ["help"] + command['topic'].split() 
  help_page   = ""

  # Open XML help file
  try:
    help_filename = os.path.join(gp_version.SRCDIR, "gp_help.xml")
    help_file = xml.dom.pulldom.parse(help_filename)
  except KeyboardInterrupt: raise
  except:
    gp_error("Error: Cannot find help source file.")
    return

  # Parse XML file, extracting any text which matches the requested topic
  path       = []
  match_list = []
  match      = False
  hits       = []
  subtopics  = []
  try:
   for event, node in help_file:
     if (event == 'START_ELEMENT'):
       path.append(node.nodeName)
       if (len(help_words) <= len(path)):
         match_list = [autocomplete(help_words[i],path[i],1) for i in range(len(help_words))]
       else:
         match_list = [False]
       match = (not False in match_list) and (len(help_words) == len(path))
       if match and (not path in hits): hits.append(path[:])
       if (not False in match_list) and (len(path) == len(help_words)+1): subtopics.append(path[-1])
     if (event == 'END_ELEMENT'):
       try:
         while (path.pop() != node.nodeName): pass
         if (len(help_words) <= len(path)):
           match_list = [autocomplete(help_words[i],path[i],1) for i in range(len(help_words))]
         else:
           match_list = [False]
         match = (not False in match_list) and (len(help_words) == len(path))
       except KeyboardInterrupt: raise
       except:
         gp_error("Error in XML help file: closing tag '%s' found, but this tag wasn't open."%node.nodeName)
         print path
         return
     if (event == 'CHARACTERS') and (len(help_words) == len(path)):
       if match: help_page += node.nodeValue
  except KeyboardInterrupt: raise
  except:
    gp_error("Error found in help source XML file whilst reading section %s."%path)
    gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return

  # Display help page
  if (len(help_page) == 0):
    gp_report("Sorry. No help was found on this topic.")
    return
  elif (len(hits) > 1):
    # Multiple pages fit request, but check whether one is shortened form of another, e.g. "grid" and "gridxaxis"
    for i in range(len(hits)):
     all_abbreviate_to_i = True
     for j in range(len(hits)):
      for k in range(len(hits[j])):
       all_abbreviate_to_i = all_abbreviate_to_i and autocomplete(hits[i][k],hits[j][k],1)
     if all_abbreviate_to_i:
      hits = [hits[i]]
      break
  if (len(hits) > 1): # STILL multiple pages fit request.
    gp_report("Ambiguous help request. The following help topics were matched:")
    for topic in hits: gp_report(reduce(lambda a,b: a+b+" ", [""]+topic))
    gp_report("Please make your help request more specific, and try again.")
  else:
    help_page = "\n**** Help Topic: %s****\n\n"%reduce(lambda a,b: a+b+" ", [""]+hits[0]) + help_page
    if (len(subtopics) < 1): help_page += "This help page has no subtopics.\n"
    else:
      help_page += "This help page has the following subtopics:\n\n"
      for i in range(len(subtopics)):
        if (i != 0): help_page += ", "
        help_page += subtopics[i]
    if (sys.stdin.isatty() and interactive):
      help_page += "\n\nPress the 'Q' key to exit this help page.\n"
    wordwrap_display(help_page, interactive)
  return
