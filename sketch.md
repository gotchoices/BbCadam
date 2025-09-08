# Sketch Command
This file describes a new top-level primitive 'sketch' for the BbCadam DSL.  The command returns a new, empty, draft sketch with an optional name.  Other commands can be chained onto the sketch to draw features in the sketch as follows:

## Feature Commands
- circle: draws a circle of a specified radius or diameter at a specified position.
- rectangle: draws a rectangle of a specified width (defaults to height) and centered at the specified position.
- polygon: draws a regular shape with N sides (default 6) of a specified length and centered at the specified position.  For even number of sides, the diameter can be specified instead of the side length.

- from: Establishes a 'first point' and 'last point' for other line, and arc commands.  Otherwise, generates nothing.
- to: draw a line from 'last point' to the specified absolute position (which becomes the new 'last point').  If only x or y is specified, the missing dimension defaults to its current ('last point') value.
- go: draw a line from 'last point' in a relative direction, specified by x and y or, alternately by r and a (polar).  Also creates new 'last point' from its ending location.
- arc: Draw an arc with a specified radius (rad) and direction (dir=cw, ccw) with one of several optional modes.  Also creates new 'last point' from its ending location.
  - quad; (1,2,3,4): A 90 degree arc in the specified quadrant (1=upper right, 2 = upper left, 3 = lower left, 4 = lower right).
  - end: Specify the endpoint of the arc, relative x,y from 'last point'.  Center must also be specified.
  - center: Specify the center of the arc, relative x,y from 'last point'.  End must also be specified.
  - endAt: Alternate absolute version of end.
  - centerAt: Alternate absolute version of center.
- close: Draw a line back to the beginning ('first point') of the current set of segments.
- exit: Explicitly exit draft mode for the sketch

## Sketch Commands
Each of these commands yields a solid which is usable like box, cylinder such that it can be added, subtracted, etc.
- pad: Pad/extrude the sketch a specified distance in a specified direction (+ or -).
- follow: Extrude the profile in the sketch along a specified path in a second sketch (path=<path_sketch>)
- revolve: Create a solid by revolving the sketch about a specified axis
