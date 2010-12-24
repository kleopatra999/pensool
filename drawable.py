#!/usr/bin/env python

import math
import coordinates
from gtk import gdk
import style
from decorators import *
import base.vector as vector





class Drawable(object):
  '''
  Things that can be drawn (morphs, glyphs, and controls).
  (Dimensions: see transformer.py.  Style: see style.py) 
  
  DRAWING:
  See below draw()
  See below virtual method put_path_to() which distinguishes subclasses.
  
  SURFACES:
  Drawing is on a surface (device or file).
  Some of this is specific to a GUI surface (a display).
  Queries, such as is_inbounds() are for GUI's.
  
  CONTROL subclasses:
  Controls are specific to a GUI, but there is no reason
  controls could not be drawn to another surface.
  
  Some controls are not actually be drawn (the background manager), 
  but data is there to support it.
  
  COORDINATES:
  !!! Note these are all ideal coordinates, not inked coordinates.
  That is, model coordinates.
  FIXME
  '''
  
  def __init__(self, viewport):
    self._dimensions = coordinates.any_dims()
    self.viewport = viewport
    self.style = style.Style()
    self.filled = False
    self.drawn_dims = coordinates.any_dims()
    
  
  # @dump_return  # Uncomment this to see drawables drawn.
  def draw(self, context):
    '''
    Draw self using context.
    Return bounds in DCS for later use to invalidate.
    
    !!! Transformation must already be in the context CTM.
    '''
    self.put_path_to(context)
    
    # Cache my drawn dimensions
    self.drawn_dims = self.get_path_bounds(context)
    
    if self.filled:
      context.fill()  # Filled, up to path
    else:
      context.stroke()  # Outline, with line width
    # Assert fill or stroke clears paths from context
    
    return self.drawn_dims
    
    
  @dump_return
  def invalidate_as_drawn(self):
    ''' 
    Invalidate means queue a region to redraw at expose event.
    GUI specific, not applicable to all surfaces.
    
    This is for composite and primitive drawables: every drawable has drawn_dims.
    '''
    self.viewport.surface.invalidate_rect( 
      coordinates.round_rect(self.drawn_dims), True )
    return self.drawn_dims
   

  '''
  invalidate_will_draw is virtual: different for composites, etc.
  '''
  def invalidate_will_draw(self):
    print "Invalidate will draw"
    pass
    
  @dump_event
  @view_altering
  def highlight(self, direction):
    '''
    Cause self to be temporarily drawn in the highlight style.
    Highlighting is a GUI focus issue, not a user document issue.
    '''
    # TODO Assume highlight is same bounds, i.e. don't invalidate before and after?
    self.style.highlight(direction)
      
      
  def dump(self):
    return repr(self) + " " + repr(self._dimensions) 
    # print "Extents:", context.path_extents()
    
    
  '''
  Dimensions: GdkRectangle of dimensions in user coordinates.
  !!! These are the dimensions, not the bounds.
  The bounds of compound drawables is computed.
  !!! Copy, not reference, in case parameters are mutable.
  '''
  
  def translate(self, point):
    '''
    transform.translate
    '''
    pass
    
    
    
    
  @dump_event
  def set_dimensions(self, dimensions):
    '''
    Set the translation and scale of an object.
    For testing: ordinarily, transforms by user actions using other methods.
    '''
    assert dimensions.width > 0
    assert dimensions.height > 0
    
    # Should be a non-empty morph (a compound)
    assert len(self) > 0
    
    # Set a copy, not a reference
    self._dimensions = coordinates.copy(dimensions)
 
    
  def get_dimensions(self):
    # Return a copy, not a reference
    return coordinates.copy(self._dimensions)
  
  """
  '''
  Note: this is a property. Properies are not polymorphic.
  Compound subclass of drawable override these by redeclaring dimensions
  as a property of Compound.
  '''
  def del_dimensions(self):
    raise RuntimeError("Can not delete dimensions.")
  dimensions = property(get_dimensions, set_dimensions, del_dimensions, 
    "GdkRectangle of dimensions in user coordinates")
  """

  def set_origin(self, coords):
    '''
    Set the origin part of the dimensions.
    That is, move without changing shape or size.
    No redraw.
    Note the origin has different meanings for different subclasses:
    it might be the upper left or it might be a hotspot or a center.
    TODO property
    '''
    self._dimensions.x = coords.x
    self._dimensions.y = coords.y
  
  def get_origin(self):
    # don't return a reference, return a copy
    return vector.Vector(self._dimensions.x, self._dimensions.y)

  def get_drawn_origin(self):
    ''' Return user coords of origin where drawn.'''
    return vector.Vector(self.drawn_dims.x, self.drawn_dims.y)
  
  
  def put_edge_to(self, context):
    '''
    Put my boundary in the context.
    For most drawables (e.g. circle), the path is the boundary.
    If NOT path is boundary, override.  E.G. text has a frame.
    This is used for hit detection.
    '''
    self.put_path_to(context)
    
    
  def is_inpath(self, user_coords):
    '''
    Does mouse hit this drawable?
    Are coords in my edge?
    
    Note user coords, not device coords.
    To hit path from a distance, ink the path wider: context.set_line_width(25)
    '''
    # TODO pass a context  .save() and restore()
    context = self.viewport.user_context()
    self.put_edge_to(context)
    hit = context.in_stroke(user_coords.x, user_coords.y)
    return hit
  
  
  def is_inbounds(self, event):
    ''' Is the event in our bounding box?'''
    # Use intersection of rectangles.
    # Convert event point to rectangle of width one.
    return coordinates.intersect(self.get_bounds(), coordinates.coords_to_bounds(event))
  
  
  @dump_return
  def center_at(self, event):
    '''
    Set ul at event.
    Center the bounding box at event.
    Assert bounding box is a rectangle.
    ??? Dimensions might not be a rectangle? TODO
    (No redraws)
    '''
    self._dimensions = coordinates.center_on_coords(self.get_bounds(), event)
    return self._dimensions # return rect so it is dumped
  
  
  def get_path_bounds(self, context):
    '''
    Get bounding rect in DCS of path in context as inked.
    '''
    x1, y1, x2, y2 = context.stroke_extents()
    x1, y1 = context.user_to_device(x1, y1)
    x2, y2 = context.user_to_device(x2, y2)
    bounds = coordinates.dimensions_from_float_extents(x1, y1, x2, y2)
    return bounds
    
    
  def get_drawn_extents(self, context):
    '''
    Extents in UCS as drawn (subject to any transformations.)
    '''
    extents = context.path_extents()
    # stroke_extents are float, avert deprecation warning
    # Truncate upper left via int()
    map(math.ceil, extents[2:3])  # ceiling bottom right
    return [int(x) for x in extents]
   
    

  def get_bounds(self):
    '''
    Return calculate rect of ideal bounding box.
    !!! Note path_extents is not ink, excludes the width of lines.
    Contrast to stroke_extents.
    '''
    context = self.viewport.user_context()
    self.put_path_to(context)
    extents = context.path_extents()
    # stroke_extents are float, avert deprecation warning
    # Truncate upper left via int()
    map(math.ceil, extents[2:3])  # ceiling bottom right
    int_extents = [int(x) for x in extents] 
    bounds = coordinates.dimensions_from_extents(*int_extents)
    # print "Bounds", bounds
    return bounds
  
    
  # TODO consolidate
  def get_inked_bounds(self):
    '''
    Return rect of inked bounding box in user coordinates.
    !!! Note stroke_extents includes the width of lines.
    '''
    context = self.viewport.user_context()
    self.put_path_to(context)
    extents = context.stroke_extents()
    # stroke_extents are float, avert deprecation warning
    # Truncate upper left via int()
    map(math.ceil, extents[2:3])  # ceiling bottom right
    int_extents = [int(x) for x in extents] 
    bounds = coordinates.dimensions_from_extents(*int_extents)
    # print "Bounds", bounds
    return bounds
 
      
  @dump_return
  def get_center(self):
    '''
    Compute center from components (not just center of self._dimensions!)
    Returns a dimensions! not a coordinates. ???
    Since objects may be laid out asymetrically,
    don't use this to get the origin !!!
    '''
    return  coordinates.center_of_dimensions(self.get_bounds())


  # Virtual methods
  
  '''
  Invalidate is virtual.
  Invalidate differs among subclasses:
  composite drawables: invalidate is aggregate
  primitive drawables: know their shape and may invalidate their shape, 
    but generally they invalidate a bounding box.

  Each subclass knows whether it is inked and transformed,
  and thus how to invalidate the proper rectangle in the viewport.
  !!! Note this is only a concern for the viewport and not other device ports.
  '''
  
  def is_in_control_area(self, event):
    '''
    Is the event in the hot area.
    Usually only for control subclass of drawable.
    '''
    raise NotImplementedError("Virtual")
    
    
  def put_path_to(self, context):
    '''
    Put path into context.
    Virtual: each subclass knows its own shape.
    '''
    raise NotImplementedError("Virtual")


  def get_orthogonal(self, point):
    '''
    Return an orthogonal unit vector at given point on boundary.
    
    Virtual: each subclass knows its own shape.
    '''
    print self
    raise NotImplementedError("Virtual")
    
    
    
    

  
      

