# GP_TICKER.PY
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

# Functions which decide where to put major / minor ticks on axes

import gp_math
import pyx
from math import *

# The maximum number of ticks along any axis

TICKS_MAXIMUM = 100

# LINEAR_TICKSEP(): Given a linear axis running from x=axis_min to x=axis_max,
# of length, and assuming labels are to have separation sep, what is the best
# list of ticks to put on axis?

def linear_ticksep(axis_min, axis_max, log_base, length, sep, ticks_overlay=[]):

  # Work out order of magnitude of range of axis
  OoM = pow(log_base, ceil(log(axis_max - axis_min, log_base)))

  # Round the limits of the axis outwards to nearest round number
  min_outer = floor(axis_min / OoM) * OoM
  max_outer = ceil (axis_max / OoM) * OoM

  # How many ticks do we want, assuming one every sep cm?
  number_ticks = floor(length / sep) + 1
  if (number_ticks > TICKS_MAXIMUM): number_ticks = TICKS_MAXIMUM # 100 ticks max
  if (number_ticks <             2): number_ticks =             2 #   2 ticks min

  best_tickscheme = []

  # Having expanded our range out to nearest factor of 10 larger than range,
  # e.g. (-10 --> 10) out to (-100 --> 100), we now try a series of possible
  # divisions of this interval, with increasing numbers of ticks.

  # Offsets mean that we can put ticks, e.g. at 0.1, 0.4, 0.7, if that is
  # useful.

  # Below is arranged in order of preference.

  for [mantissa_footprint,ticksep,offset] in tickschemes(OoM, log_base, False): # List of [ Tick sep, Offset from min_outer ]s
    ts_min = min_outer+offset
    ticks  = []
    for i in range(0,int(1.5+float(max_outer-min_outer)/ticksep)):
     x = ts_min + i*ticksep
     ticks.append([ x , log_textoutput(x, None, log_base) ]) # Make a list of ticks, with format [x, label]

    # Remove any ticks which fall off the end of the axis
    while (len(ticks)>0) and gp_math.islessthan(ticks[0][0],axis_min):     ticks = ticks[1:]
    while (len(ticks)>0) and gp_math.isgreaterthan(ticks[-1][0],axis_max): ticks = ticks[:-1]

    # Make sure that this set of ticks overlays ticks_overlay
    matched = True
    for [xo,lo] in ticks_overlay:
     matched = False
     for i in range(len(ticks)):
      [x,l] = ticks[i]
      if (x==xo):
       ticks = ticks[:i]+ticks[i+1:]
       matched = True
       break
     if not matched: break
    if not matched: continue

    if (len(ticks) > number_ticks): break # If we have too many ticks, we've already found are best ticking scheme
    if (len(ticks) > len(best_tickscheme)): best_tickscheme = ticks # If this scheme produces no more ticks than last, the first was better.

  return best_tickscheme 

# TICKSCHEMES(): Returns a list of [ Tick sep, Offset from min_outer ]s
# for possible linear tick schemes.

def tickschemes(OoM, log_base, log=False):
 tick_schemes = []
 factors = gp_math.factorise(log_base)
 factors.reverse() # We descend to smaller and smaller step multiples

 OoMscan = OoM / log_base
 if log and (OoMscan == 1.0/log_base):
  tickschemes_log(log, tick_schemes)
 else:
  for step in range(int(log_base/2),0,-1): # For the first OoM, we can divide into any integer step, with any offset from axis mimimum
   for offset in range(0,step): # e.g. 1,2,3,4,5 or 0,3,6,9 or 1,4,7 or 2,5,8.
    tick_schemes.append([[1] , step*OoMscan , offset*OoMscan])

 level_descend = 2 # Once we go below top level OoM, into dividing up several orders of magnitude, we any split into factor multiples
 while (pow(log_base,level_descend-1) < (log_base * TICKS_MAXIMUM)):
  OoMscan = OoM / pow(log_base, level_descend) # e.g. 0.0, 0.5, 1.0, 1.5, 2.0 or 0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2
  if log and (OoMscan == 1.0/log_base):
   tickschemes_log(log, tick_schemes)
  else:
   for step in factors:
    tick_schemes.append([[1] , step*OoMscan , 0.0 ])
  level_descend = level_descend + 1
 return tick_schemes

# TICKSCHEMES_LOG(): When our axis is a log axis, we divide up single orders of
# magnitude differently from tenths, tens or hundreds of orders of magnitude.
# We try as best we can to divide into into equal halfs, thirds, quarters, etc.

def tickschemes_log(log, tick_schemes):
 divisor = 1
 stopping = False
 while not stopping:
  mantissas = []
  for i in range(0,divisor):
   mantissas.append(int(floor(pow(log,float(i)/divisor)+0.5)))
   if (i > 0) and (mantissas[-1] == mantissas[-2]):
    stopping = True
    break
  divisor = divisor + 1
  if not stopping:
   tick_schemes.append([mantissas, 1.0, 0.0]) # Multiply by 10.0, as log_base was 10.0 in tickschemes above
 tick_schemes.append([range(1,log), 1.0, 0.0])

# LINEAR_TICKS_REALISE(): Convert a [min,step,max] structure into a list of
# tick points

def linear_ticks_realise(min,step,max,log_base):
 if (step == 0): return []
 ticks_range     = max-min
 ticks_out       = []
 tick            = min
 while (not gp_math.isgreaterthan(tick, max)) and (len(ticks_out) < TICKS_MAXIMUM):
  ticks_out.append( [ tick , log_textoutput(tick, None, log_base) ] )
  tick = tick + step
 return ticks_out

# LOG_TICKS_REALISE(): Convert a [min,step,max] structure into a list of tick points

def log_ticks_realise(min,step,max,log_base):
 if (step in [0,1]): return []
 ticks_range     = max-min
 ticks_out       = []
 tick            = min
 while (not gp_math.isgreaterthan(tick, max)) and (len(ticks_out) < TICKS_MAXIMUM):
  ticks_out.append( [ tick , log_textoutput(tick, None, log_base) ] )
  tick = tick * step
 return ticks_out

# LOG_TICKSEP(): Given a log axis running from x=axis_min to x=axis_max,
# of length, and assuming labels are to have separation sep, what is the best
# {start,incr,stop} for the ticks?

def log_ticksep(axis_min, axis_max, log_base, length, sep, ticks_overlay=[]):

  # Work out order of magnitude of range of axis in log space
  axis_minl = log(axis_min, log_base)
  axis_maxl = log(axis_max, log_base)
  OoM = pow(10.0, ceil(log10(axis_maxl - axis_minl)))

  # Round the log-limits of the axis outwards to nearest round number
  min_outer = floor(axis_minl / OoM) * OoM
  max_outer = ceil (axis_maxl / OoM) * OoM

  # How many ticks do we want, assuming one every sep cm?
  number_ticks = floor(length / sep) + 1
  if (number_ticks > TICKS_MAXIMUM): number_ticks = TICKS_MAXIMUM # 100 ticks max
  if (number_ticks <             2): number_ticks =             2 #   2 ticks min

  best_tickscheme = []

  # Having expanded our range out to nearest factor of 10 larger than range,
  # e.g. (-10 --> 10) out to (-100 --> 100), we now try a series of possible
  # divisions of this interval, with increasing numbers of ticks.

  # Offsets mean that we can put ticks, e.g. at 0.1, 0.4, 0.7, if that is
  # useful.

  # Below is arranged in order of preference.

  for [mantissa_footprint,ticksep,offset] in tickschemes(OoM, 10.0, log_base):
    ts_min = min_outer+offset
    ticks  = []
    for i in range(0,int(1.5+(max_outer-min_outer)/ticksep)):
     # NB: We store x positions in log form until we've trimmed the ends to user's range, to prevent overflows
     for m in mantissa_footprint:
      exponent = ts_min + i*ticksep
      x        = exponent           + log(m, log_base)
      ticks.append([ x , log_textoutput(m, exponent, log_base) ])

    # Remove any ticks which fall off the end of the axis
    while (len(ticks)>0) and gp_math.islessthan   (ticks[ 0][0],axis_minl): ticks = ticks[1:  ]
    while (len(ticks)>0) and gp_math.isgreaterthan(ticks[-1][0],axis_maxl): ticks = ticks[ :-1]

    # Now exponentiate x positions, having trimmed our list to user range
    for tick in ticks: tick[0] = pow(log_base, tick[0])

    # Make sure that this set of ticks overlays ticks_overlay
    matched = True
    for [xo,lo] in ticks_overlay:
     matched = False
     for i in range(len(ticks)):
      [x,l] = ticks[i]
      if (x==xo):
       ticks = ticks[:i]+ticks[i+1:]
       matched = True
       break
     if not matched: break
    if not matched: continue

    # The following line is a FUDGE to make log axes look favourably upon putting minor ticks at every unit mantissa
    if (len(mantissa_footprint) == (log_base-1)) and (ticks_overlay != []):
      if (len(ticks) > (number_ticks*3)): break
      best_tickscheme = ticks
    elif (len(mantissa_footprint) > 1) and (ticks_overlay != []) and (len(ticks) > number_ticks):
      continue
    else:
      if (len(ticks) > number_ticks): break # If we have too many ticks, we've already found are best ticking scheme
      if (len(ticks) > len(best_tickscheme)): best_tickscheme = ticks # If this scheme produces no more ticks than last, the first was better.

  return best_tickscheme

# LOG_TEXTOUTPUT(): Takes i*10^x, and works out best format to output it in

def log_textoutput(mantissa, exponent, logbase):
 if (mantissa < 0.0): sign = "-" ; mantissa = fabs(mantissa)
 else               : sign = ""

 if (exponent == None): # If exponent is none, we need to do exponent/mantissa decomposition
  if (mantissa == 0.0):
   exponent = 1
  else:
   exponent = gp_math.getexponent(mantissa, logbase)
   mantissa = gp_math.getmantissa(mantissa, logbase)

 logbase_str = gp_math.val2string(logbase)
 exp_str     = gp_math.val2string(exponent)
 man_str     = gp_math.val2string(mantissa)    

 if (fabs(exponent) >  3) or (not gp_math.isinteger(exponent)):
  if (mantissa != 1): output = sign + r"%s \times %s^{%s}"%(man_str,logbase_str,exp_str) # format for "5 * 10^n"
  else              : output = sign + r"%s^{%s}"%(logbase_str,exp_str)                   # format for "10^n"
 else:
  value_str = gp_math.val2string(mantissa * pow(logbase,exponent))
  output = sign + value_str # format for "0.1", "1" , "10" , "100" or "1000"

 return "$"+output+"$"

# TICKS_PYX(): Convert a list of ticks into PyX tick objects

# exclude_list is a mechanism for stopping major ticks from colliding with
# minor ticks. PyX wails if this happens.

def ticks_pyx(tick_pos_list, ticklevel, axis_min, axis_max, exclude_list=[]):
 ticks_pyx_out = []
 tick_prev_x = None
 for tick in tick_pos_list:
  exclude = False
  if gp_math.islessthan(tick[0],axis_min) or gp_math.isgreaterthan(tick[0],axis_max): continue # Don't put ticks beyond axis ends
  for i in range(len(exclude_list)): # Stop minor ticks from colliding with major ticks
   if gp_math.isequal(tick[0], exclude_list[i][0], 1e-8): # Experimentally, 1e8 seems to be the tolerance that PyX uses
    exclude = True
    break 
  if (tick_prev_x != None) and gp_math.isequal(tick[0], tick_prev_x, 1e-8): exclude = True

  if not exclude:
   if (ticklevel == 0): label = tick[1]
   else               : label = ""
   ticks_pyx_out.append(pyx.graph.axis.tick.tick(tick[0], label=label, ticklevel=ticklevel))
   tick_prev_x = tick[0]

 return ticks_pyx_out

# GETTICKS(): Generalisation of the two functions below.

def getticks(axis, axis_length, sepmaj, sepmin, ticks_realise, ticksep, axis_type):

  # Find out essential information about axis 
  axis_min   = min(axis['MIN_RANGE'], axis['MAX_RANGE'])
  axis_max   = max(axis['MIN_RANGE'], axis['MAX_RANGE'])
  axis_set   = axis['SETTINGS']
  axis_base  = axis['SETTINGS']['LOGBASE']

  tick_sets = {}

  for [TICKLIST,TICKMIN,TICKSTEP,TICKMAX,TICKSET] in [[ 'TICKLIST', 'TICKMIN', 'TICKSTEP', 'TICKMAX', 'major'],
                                                      ['MTICKLIST','MTICKMIN','MTICKSTEP','MTICKMAX', 'minor'] ] :

    if   (axis_set[TICKLIST] != None):
      tick_sets[TICKSET] = []
      for [x,l] in axis_set[TICKLIST]:
        if (l == None): l = log_textoutput(x, None, axis_base)
        tick_sets[TICKSET].append( [x,l] )
    elif (axis_set[TICKSTEP] != None):
      tmin  = axis_set[TICKMIN]
      tstep = axis_set[TICKSTEP]
      tmax  = axis_set[TICKMAX]
      if (tmin == None): tmin = axis_min
      if (tmax == None): tmax = axis_max
      tick_sets[TICKSET] = ticks_realise(tmin,tstep,tmax,axis_base) # Either linear_ticks_realise or log_ticks_realise; selected in wrappers below
    else:
      if (TICKSET == "major"):
        tick_sets[TICKSET] = ticksep(axis_min, axis_max, axis_base, axis_length, sepmaj) # Likewise linear_ticksep or log_ticksep
      else:
        tick_sets[TICKSET] = ticksep(axis_min, axis_max, axis_base, axis_length, sepmin, tick_sets["major"]) # Minor ticks must overlay major ticks

  pyx_ticks_maj = ticks_pyx(tick_sets["major"], 0, axis_min, axis_max)
  pyx_ticks_min = ticks_pyx(tick_sets["minor"], 1, axis_min, axis_max, tick_sets["major"])

  return pyx_ticks_maj + pyx_ticks_min

# LINEAR_GETTICKS(): Called from gp_plot. Main interface with the outside world.

def linear_getticks(axis, axis_length, sepmaj, sepmin):
  return getticks(axis, axis_length, sepmaj, sepmin, linear_ticks_realise, linear_ticksep, "linear")

# LOG_GETTICKS(): Called from gp_plot. Main interface with the outside world.

def log_getticks(axis, axis_length, sepmaj, sepmin):
  return getticks(axis, axis_length, sepmaj, sepmin, log_ticks_realise   , log_ticksep   , "log"   )

