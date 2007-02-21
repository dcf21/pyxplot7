# GP_AUTOCOMPLETE.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
#
# $Id: gp_autocomplete.py,v 1.22 2007/02/21 03:48:00 dcf21 Exp $
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

alphabetic_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_"

# AUTOCOMPLETE(): Return TRUE if input string first word matches the first few
# letters of test (minimum min letters)

# Returns integer, which is position of first character not matched, plus one.
# We add one so that if min=0, we can return position zero and still have an
# integer value equivalent to TRUE.

def autocomplete(input, test, min):
  alphabetic = True
  for char in test:
   if char not in alphabetic_chars:
    alphabetic = False # Is string we are matching is all letters, it can be terminated with punctuation

  i = 0
  input2 = input.strip() # Strip leading/trailing spaces
  while (i < len(input2)):
    if (i < len(test)):
      if (input2[i].capitalize() != test[i].capitalize()):
        if (input2[i].isspace()) or (alphabetic and input2[i] not in alphabetic_chars): break
        else: return (0 == 1) # We hit a character which isn't in test string
    else:
      if (input2[i].isspace()) or (alphabetic and input2[i] not in alphabetic_chars): return i+1
      else                                                                          : return 0
    i=i+1
  if (i >= min): return i+1 # We read > than minimum number of characters before hitting whitespace
  return 0 # We didn't
