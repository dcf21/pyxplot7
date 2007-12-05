# GP_COMMANDS.PY
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

# The language used in this file is generally refered to as RE++.  The atoms of the syntax are summarised below.
#
# =                      If a match fails after this point generate an error rather than continuing
# text@3:var             Match "text", abbreviated to >= 3 letters, and place in variable var
# text@n                 No space after "text", which must be quoted in full
# { ... }                Optionally match ...
# < ...a... | ...b... >  Match exactly one of ...a... or ...b...
# ( ...a... ~ ...b... )  Match ...a..., ...b..., etc., in any order, either 1 or 0 times each
# %q:variable            Match a quoted string ('...' or "...") and place it in variable
# %S:variable            Match an unquoted string and place it in variable 
# %f:variable            Match a float and place it in variable 
# %d:variable            Match an integer and place it in variable

# List of commands recognised by PyXPlot

commands = r"""
arrow@2:directive = { from@1 } %f:x1 ,@n %f:y1 to@1 %f:x2 ,@n %f:y2 { with@1 ( < linetype@5 | lt@2 > %d:linetype ~ < linewidth@5 | lw@2 > %f:linewidth ~ < linestyle@6 | ls@2 > %d:linestyle ~ < colour@1 | color@1 > %s:colour ~ < nohead@2:arrow_style | head@2:arrow_style | twohead@2:arrow_style | twoway@2:arrow_style:twohead > ) } 
cd@2:directive = [ < %q:directory | %Q:directory | %S:directory > ]:path
clear@3:directive =
delete@3:directive = [ %d:number ]:deleteno,
edit@2:directive = %d:editno
eps@2:directive = < %q:filename | %Q:filename | %S:filename > ( at@2 %f:x ,@n %f:y ~ rotate@1 %f:rotation ~ width@1 %f:width ~ height@1 %f:height )
exec@3:directive: = < %q:command | %Q:command >
exit@2:directive:quit =
fit@3:directive = [ \[@n { { < %f:min | \*@n:minauto > } < :@n | to@n > { < %f:max | \*@n:maxauto > } } \]@n ]:range_list %v:fit_function \(@n [ %v:inputvar ]:operands, \)@n < %q:filename | %Q:filename | %S:filename > ( every@1 [ { %d:every_item } ]:every_list: ~ index@1 %f:index ~ select@1 %E:select_criterion { < continuous@1:select_cont | discontinuous@1:select_cont > } ~ using@1 { < rows@1:use_rows | columns@1:use_columns > } [ %E:using_item ]:using_list: ) via@1 [ %v:fit_variable ]:fit_variables,
help@2:directive = %r:topic
history@6:directive = { %d:number_lines }
histogram@2:directive = [ \[@n { { < %f:min | \*@n:minauto > } < :@n | to@n > { < %f:max | \*@n:maxauto > } } \]@n ]:range_list %v:hist_function \()@2 < %q:filename | %Q:filename | %S:filename > ( every@1 [ { %d:every_item } ]:every_list: ~ index@1 %f:index ~ select@1 %E:select_criterion { < continuous@1:select_cont | discontinuous@1:select_cont > } ~ using@1 { < rows@1:use_rows | columns@1:use_columns > } [ %E:using_item ]:using_list: ~ binwidth@4 %f:binwidth ~ binorigin@4 %f:binorigin ~ bins@n \(@n [ %f:x ]:bin_list, \)@n )
< jpeg@1:directive | jpg@2:directive:jpeg > = < %q:filename | %Q:filename | %S:filename > ( at@2 %f:x ,@n %f:y ~ rotate@1 %f:rotation ~ width@1 %f:width ~ height@1 %f:height )
load@2:directive = < %q:filename | %Q:filename | %S:filename >
move@3:directive = %d:moveno to@1 %f:x ,@n %f:y 
?@n:directive:help = %r:topic 
!@n:directive:pling = %r:cmd
< plot@1:directive | replot@3:directive > = [ \[@n { { < %f:min | \*@n:minauto > } < :@n | to@n > { < %f:max | \*@n:maxauto > } } \]@n ]:range_list [ < %q:filename | [ %e:expression ]:expression_list: > ( axes@1 %a:axis_x %a:axis_y ~ every@1 [ { %d:every_item } ]:every_list: ~ index@1 %f:index ~ select@1 %E:select_criterion { < continuous@1:select_cont | discontinuous@1:select_cont > } ~ < title@1 < %q:title | %Q:title > | notitle@3:notitle > ~ using@1 { < rows@1:use_rows | columns@1:use_columns > } [ %E:using_item ]:using_list: ) { with@1 ( < linetype@5 | lt@2 > %d:linetype ~ < linewidth@5 | lw@2 > %f:linewidth ~ < pointsize@7 | ps@2 > %f:pointsize ~ < pointtype@6 | pt@2 > %d:pointtype ~ < linestyle@6 | ls@2 > %d:linestyle ~ < pointlinewidth@6 | plw@3 > %f:pointlinewidth ~ < colour@1 | color@1 > %s:colour ~ < fillcolour@2 | fillcolor@2 | fc@2 > %s:fillcolour ~ < lines@1:style | points@1:style | lp@2:style:linespoints | linespoints@5:style | pl@2:style:linespoints | pointslines@5:style:linespoints | dots@1:style | boxes@1:style | wboxes@1:style | impulses@1:style | steps@1:style | fsteps@1:style | histeps@1:style | errorbars@1:style | xerrorbars@2:style | yerrorbars@2:style | xyerrorbars@3:style | errorrange@6:style | xerrorrange@7:style | yerrorrange@7:style | xyerrorrange@8:style | arrows@3:style:arrows_head | arrows_head@3:style | arrows_nohead@3:style | arrows_twoway@3:style | arrows_twohead@3:style | csplines@3:style | acsplines@3:style > ~ smooth@2:smooth ) } ]:plot_list, 
print@2:directive = [ < %q:string | %f:expression | %Q:string > ]:print_list, 
pwd@2:directive =
quit@1:directive =
refresh@3:directive =
reset@3:directive =
save@2:directive = < %q:filename | %Q:filename | %S:filename >
set@2:directive %a:axis label@1:set_option:xlabel = < %q:label_text | %Q:label_text | %s:label_text >
set@2:directive %a:axis range@1:set_option = \[@n { { < %f:min | \*@n:minauto > } < :@n | to@n > { < %f:max | \*@n:maxauto > } } \]@n
set@2:directive { %a:axis } ticdir@4:set_option = < inward@1:dir | outward@1:dir | both@1:dir >
set@2:directive { m@n:minor } { %a:axis } tics@1:set_option = { < axis@1:dir:inward | border@1:dir:outward | inward@1:dir | outward@1:dir | both@1:dir > } { < autofreq@1:autofreq | %f:start { ,@n %f:increment { ,@n %f:end } } | \(@n [ { %q:label } %f:x ]:tick_list, \)@n > }
set@2:directive arrow@1:set_option = %d:arrow_id { from@1 } { < first@1:x1_system | second@1:x1_system | screen@2:x1_system | graph@1:x1_system | axis@n %d:x1_system > } %f:x1 ,@n { < first@1:y1_system | second@1:y1_system | screen@2:y1_system | graph@1:y1_system | axis@n %d:y1_system > } %f:y1 to@1 { < first@1:x2_system | second@1:x2_system | screen@2:x2_system | graph@1:x2_system | axis@n %d:x2_system > } %f:x2 ,@n { < first@1:y2_system | second@1:y2_system | screen@2:y2_system | graph@1:y2_system | axis@n %d:y2_system > } %f:y2 { with@1 ( < linetype@5 | lt@2 > %d:linetype ~ < linewidth@5 | lw@2 > %f:linewidth ~ < linestyle@6 | ls@2 > %d:linestyle ~ < colour@1 | color@1 > %s:colour ~ < nohead@2:arrow_style | head@2:arrow_style | twohead@2:arrow_style | twoway@2:arrow_style:twohead > ) }
set@2:directive autoscale@2:set_option = [ %a:axis ]:axes
set@2:directive axescolor@5:set_option:axescolour = %s:colour
set@2:directive axescolour@5:set_option = %s:colour
set@2:directive axis@1:set_option = [ %a:axis ]:axes
set@2:directive backup@1:set_option =
set@2:directive bar@2:set_option = < large@1:bar_size:1 | small@1:bar_size:0 | %f:bar_size >
set@2:directive binorigin@4:set_option = %f:bin_origin
set@2:directive binwidth@4:set_option = %f:bin_width
set@2:directive boxfrom@4:set_option = %f:box_from
set@2:directive boxwidth@1:set_option = %f:box_width
set@2:directive < data@1:dataset_type style@1:set_option | style@2:set_option data@1:dataset_type > = ( < linetype@5 | lt@2 > %d:linetype ~ < linewidth@5 | lw@2 > %f:linewidth ~ < pointsize@7 | ps@2 > %f:pointsize ~ < pointtype@6 | pt@2 > %d:pointtype ~ < linestyle@6 | ls@2 > %d:linestyle ~ < pointlinewidth@6 | plw@3 > %f:pointlinewidth ~ < colour@1 | color@1 > %s:colour ~ < fillcolour@2 | fillcolor@2 | fc@2 > %s:fillcolour ~ < lines@1:style | points@1:style | lp@2:style:linespoints | linespoints@5:style | pl@2:style:linespoints | pointslines@5:style:linespoints | dots@1:style | boxes@1:style | wboxes@1:style | impulses@1:style | steps@1:style | fsteps@1:style | histeps@1:style | errorbars@1:style | xerrorbars@2:style | yerrorbars@2:style | xyerrorbars@3:style | errorrange@6:style | xerrorrange@7:style | yerrorrange@7:style | xyerrorrange@8:style | arrows_head@3:style | arrows_nohead@3:style | arrows_twoway@3:style | arrows_twohead@3:style | csplines@3:style | acsplines@3:style > ~ smooth@2:smooth )
set@2:directive display@1:set_option =
set@2:directive dpi@3:set_option = %f:dpi
set@2:directive fontsize@1:set_option = %d:fontsize
set@2:directive fountsize@1:set_option:fontsize = %d:fontsize
set@2:directive < function@1:dataset_type style@1:set_option | style@2:set_option function@1:dataset_type > = ( < linetype@5 | lt@2 > %d:linetype ~ < linewidth@5 | lw@2 > %f:linewidth ~ < pointsize@7 | ps@2 > %f:pointsize ~ < pointtype@6 | pt@2 > %d:pointtype ~ < linestyle@6 | ls@2 > %d:linestyle ~ < pointlinewidth@6 | plw@3 > %f:pointlinewidth ~ < colour@1 | color@1 > %s:colour ~ < fillcolour@2 | fillcolor@2 | fc@2 > %s:fillcolour ~ < lines@1:style | points@1:style | lp@2:style:linespoints | linespoints@5:style | pl@2:style:linespoints | pointslines@5:style:linespoints | dots@1:style | boxes@1:style | wboxes@1:style | impulses@1:style | steps@1:style | fsteps@1:style | histeps@1:style | errorbars@1:style | xerrorbars@2:style | yerrorbars@2:style | xyerrorbars@3:style | errorrange@6:style | xerrorrange@7:style | yerrorrange@7:style | xyerrorrange@8:style | arrows_head@3:style | arrows_nohead@3:style | arrows_twoway@3:style | arrows_twohead@3:style | csplines@3:style | acsplines@3:style > ~ smooth@2:smooth )
set@2:directive grid@1:set_option = [ %a:axis ]:axes
set@2:directive gridmajcolor@6:set_option:gridmajcolour = %s:colour
set@2:directive gridmajcolour@6:set_option = %s:colour
set@2:directive gridmincolor@6:set_option:gridmincolour = %s:colour
set@2:directive gridmincolour@6:set_option = %s:colour
set@2:directive key@1:set_option = < below@2:pos | above@2:pos | outside@1:pos | ( < left@1:xpos | right@1:xpos | xcentre@1:xpos | xcenter@1:xpos:xcentre > ~ < top@1:ypos | bottom@2:ypos | ycentre@1:ypos | ycenter@1:ypos:ycentre > ) > { %f:x_offset ,@n %f:y_offset }
set@2:directive keycolumns@4:set_option = %d:key_columns
set@2:directive label@2:set_option = %d:label_id < %q:label_text | %Q:label_text | %s:label_text > { at@1 } { < first@1:x_system | second@1:x_system | screen@2:x_system | graph@1:x_system | axis@n %d:x_system > } %f:x_position ,@n { < first@1:y_system | second@1:y_system | screen@2:y_system | graph@1:y_system | axis@n %d:y_system > } %f:y_position { rotate@1 %f:rotation } { with@1 < colour@1 | color@1 > %s:colour }
set@2:directive < linestyle@1:set_option | ls@2:set_option:linestyle > = %d:linestyle_id ( < linetype@5 | lt@2 > %d:linetype ~ < linewidth@5 | lw@2 > %f:linewidth ~ < pointsize@7 | ps@2 > %f:pointsize ~ < pointtype@6 | pt@2 > %d:pointtype ~ < linestyle@6 | ls@2 > %d:linestyle ~ < pointlinewidth@6 | plw@3 > %f:pointlinewidth ~ < colour@1 | color@1 > %s:colour ~ < fillcolour@2 | fillcolor@2 | fc@2 > %s:fillcolour ~ < lines@1:style | points@1:style | lp@2:style:linespoints | linespoints@5:style | pl@2:style:linespoints | pointslines@5:style:linespoints | dots@1:style | boxes@1:style | wboxes@1:style | impulses@1:style | steps@1:style | fsteps@1:style | histeps@1:style | errorbars@1:style | xerrorbars@2:style | yerrorbars@2:style | xyerrorbars@3:style | errorrange@6:style | xerrorrange@7:style | yerrorrange@7:style | xyerrorrange@8:style | arrows_head@3:style | arrows_nohead@3:style | arrows_twoway@3:style | arrows_twohead@3:style | csplines@3:style | acsplines@3:style > ~ smooth@2:smooth )
set@2:directive < linewidth@5:set_option | lw@2:set_option:linewidth > = %f:linewidth
set@2:directive logscale@1:set_option = [ %a:axis ]:axes { %d:base }
set@2:directive multiplot@1:set_option =
set@2:directive:unset noarrow@3:set_option:arrow = [ %d:arrow_id ]:arrow_list,
set@2:directive:unset noaxis@3:set_option:axis = [ %a:axis ]:axes
set@2:directive nobackup@3:set_option =
set@2:directive nodisplay@3:set_option =
set@2:directive nogrid@3:set_option = [ %a:axis ]:axes
set@2:directive nokey@3:set_option =
set@2:directive:unset nolabel@4:set_option:label = [ %d:label_id ]:label_list,
set@2:directive:unset nolinestyle@3:set_option:linestyle = [ %d:id ]:linestyle_ids,
set@2:directive nologscale@3:set_option = [ %a:axis ]:axes { %d:base }
set@2:directive nomultiplot@3:set_option =
set@2:directive no@n { m@n:minor } { %a:axis } tics:set_option:notics =
set@2:directive notitle@3:set_option =
set@2:directive origin@2:set_option = %f:x_origin ,@n %f:y_origin
set@2:directive output@1:set_option = < %q:filename | %Q:filename | %S:filename >
set@2:directive palette@1:set_option = [ < %q:colour | %Q:colour | %s:colour > ]:palette,
set@2:directive papersize@3:set_option %f:x_size ,@n %f:y_size =
set@2:directive papersize@3:set_option = < %q:paper_name | %Q:paper_name | %s:paper_name >
set@2:directive < pointlinewidth@6:set_option | plw@3:set_option:pointlinewidth > = %f:pointlinewidth
set@2:directive < pointsize@1:set_option | ps@2:set_option:pointsize > = %f:pointsize
set@2:directive preamble@2:set_option = %r:preamble
set@2:directive samples@2:set_option = %d:samples
set@2:directive size@1:set_option = < %f:width | ratio@1 %f:ratio | noratio@1:noratio | square@1:square >
set@2:directive terminal@1:set_option = ( < x11_singlewindow@1:term:X11_singlewindow | x11_multiwindow@5:term:X11_multiwindow | x11_persist@5:term:X11_persist | postscript@1:term:PS | ps@2:term:PS | eps@1:term:EPS | pdf@2:term:PDF | png@2:term:PNG | gif@1:term:GIF | jpg@1:term:JPG | jpeg@1:term:JPG > ~ < colour@1:col:ON | color@1:col:ON | monochrome@1:col:OFF > ~ < enlarge@1:enlarge:ON | noenlarge@3:enlarge:OFF > ~ < landscape@1:land:ON | portrait@2:land:OFF > ~ < transparent@1:trans:ON | solid@1:trans:OFF > ~ < invert@1:invert:ON | noinvert@1:invert:OFF > ~ < antialias@1:antiali:ON | noantialias@3:antiali:OFF > )
set@2:directive textcolor@5:set_option:textcolour = %s:colour
set@2:directive textcolour@5:set_option = %s:colour
set@2:directive texthalign@5:set_option = < left@1:left | centre@1:centre | center@1:centre | right@1:right >
set@2:directive textvalign@5:set_option = < top@1:top | centre@1:centre | center@1:centre | bottom@1:bottom >
set@2:directive title@2:set_option = < %q:title | %Q:title | %s:title > { %f:x_offset ,@n %f:y_offset }
set@2:directive width@1:set_option:size = %f:width
set@2:directive:set_error = { %s:set_option } %r:restofline
show@2:directive = [ %s:setting ]:setting_list
spline@3:directive = [ \[@n { { < %f:min | \*@n:minauto > } < :@n | to@n > { < %f:max | \*@n:maxauto > } } \]@n ]:range_list %v:fit_function \()@2 < %q:filename | %Q:filename | %S:filename > ( every@1 [ { %d:every_item } ]:every_list: ~ index@1 %f:index ~ select@1 %E:select_criterion { < continuous@1:select_cont | discontinuous@1:select_cont > } ~ smooth@1 %f:smooth ~ using@1 { < rows@1:use_rows | columns@1:use_columns > } [ %E:using_item ]:using_list: )
tabulate@2:directive = [ \[@n { { < %f:min | \*@n:minauto > } < :@n | to@n > { < %f:max | \*@n:maxauto > } } \]@n ]:range_list ( [ < %q:filename | [ %e:expression ]:expression_list: > ( every@1 [ { %d:every_item } ]:every_list: ~ index@1 %f:index ~ select@1 %E:select_criterion { < continuous@1:select_cont | discontinuous@1:select_cont > } ~ using@1 { < rows@1:use_rows | columns@1:use_columns > } [ %E:using_item ]:using_list: ) ]:tabulate_list, ~ with@1 ( format@1 < %q:format | %Q:format > ) )
text@3:directive = < %q:string | %Q:string | %s:string > ( at@1 %f:x ,@n %f:y ~ rotate@1 %f:rotation ) { with@1 < colour@1 | color@1 > %s:colour }
undelete@3:directive = [ %d:number ]:undeleteno,
unset@3:directive %a:axis label@1:set_option:xlabel =
unset@3:directive %a:axis range@1:set_option =
unset@3:directive { %a:axis } ticdir@1:set_option =
unset@3:directive { no@n } { m@n:minor } { %a:axis } tics@1:set_option = 
unset@3:directive arrow@2:set_option = [ %d:arrow_id ]:arrow_list,
unset@2:directive autoscale@2:set_option = [ %a:axis ]:axes
unset@3:directive axescolor@5:set_option:axescolour =
unset@3:directive axescolour@5:set_option =
unset@3:directive axis@2:set_option = [ %a:axis ]:axes
unset@3:directive backup@1:set_option =
unset@3:directive bar@2:set_option =
unset@3:directive boxfrom@4:set_option =
unset@3:directive boxwidth@1:set_option =
unset@3:directive display@1:set_option =
unset@3:directive dpi@3:set_option =
unset@3:directive fontsize@1:set_option =
unset@3:directive fountsize@1:set_option:fontsize =
unset@3:directive grid@1:set_option =
unset@3:directive gridmajcolor@6:set_option:gridmajcolour =
unset@3:directive gridmajcolour@6:set_option =
unset@3:directive gridmincolor@6:set_option:gridmincolour =
unset@3:directive gridmincolour@6:set_option =
unset@3:directive key@1:set_option =
unset@3:directive keycolumns@4:set_option =
unset@3:directive label@2:set_option = [ %d:label_id ]:label_list,
unset@3:directive < linestyle@1:set_option | ls@2:set_option:linestyle > = [ %d:id ]:linestyle_ids,
unset@3:directive < linewidth@5:set_option | lw@2:set_option:linewidth > =
unset@3:directive:set logscale@1:set_option:nologscale = [ %a:axis ]:axes
unset@3:directive multiplot@1:set_option =
unset@3:directive noarrow@3:set_option:arrow = [ %d:arrow_id ]:arrow_list,
unset@3:directive noaxis@4:set_option:axis = [ %a:axis ]:axes
unset@3:directive nobackup@3:set_option:backup =
unset@3:directive nodisplay@3:set_option:display =
unset@3:directive nogrid@3:set_option:grid =
unset@3:directive nokey@3:set_option:key =
unset@3:directive nolabel@4:set_option:label = [ %d:label_id ]:label_list,
unset@3:directive < nolinestyle@3:set_option:linestyle | nols@4:set_option:linestyle > = [ %d:id ]:linestyle_ids,
unset@3:directive < nolinewidth@7:set_option:linewidth | nolw@4:set_option:linewidth >
unset@3:directive:set nologscale@3:set_option = [ %a:axis ]:axes { %d:base }
unset@3:directive nomultiplot@3:set_option:multiplot =
unset@3:directive notitle@3:set_option:title =
unset@3:directive origin@2:set_option =
unset@3:directive output@1:set_option =
unset@3:directive palette@1:set_option =
unset@3:directive papersize@3:set_option =
unset@3:directive < pointlinewidth@6:set_option |  plw@3:set_option:pointlinewidth > =
unset@3:directive < pointsize@1:set_option | ps@2:set_option:pointsize > =
unset@3:directive preamble@2:set_option =
unset@3:directive samples@2:set_option =
unset@3:directive:set < axis@1:set_option:noaxis | noaxis@3:set_option > = [ %a:axis ]:axes
unset@3:directive size@1:set_option =
unset@3:directive terminal@1:set_option =
unset@3:directive textcolor@5:set_option:textcolour =
unset@3:directive textcolour@5:set_option =
unset@3:directive texthalign@5:set_option =
unset@3:directive textvalign@5:set_option =
unset@3:directive title@2:set_option =
unset@3:directive width@1:set_option =
unset@3:directive:unset_error = { %s:set_option } %r:restofline
{ < let@3 | set@3 > } %v:varname \=~@n:directive:var_set_regex  = s@n %r:regex
{ < let@3 | set@3 > } %v:varname \=@n:directive:var_set = { < %f:value | %Q:value | %q:value > }
"""
