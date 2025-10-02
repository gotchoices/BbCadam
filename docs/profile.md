# 3D Profile Enhancement Strategy

## Overview

This document outlines the strategy for enhancing the current `section` functionality to support 3D operations while maintaining backward compatibility with existing 2D workflows.

## Current State Analysis

### Current Architecture
- **`sketch`**: Sketcher-based, 2D only, materialized objects
- **`section`**: Part-based, 2D profiles → 3D solids via pad/revolve/sweep
- **Shared**: Both use `_SectionProfile` for 2D geometry storage

### Current Limitations
- **2D only**: All path creation is constrained to 2D planes
- **Plane-bound**: Operations limited to XY, XZ, YZ planes
- **No 3D paths**: Cannot create complex 3D paths for sweeping

## Enhancement Strategy

### 1. Rename and Restructure

**Rename `section` → `profile`**
- More generic name that encompasses both 2D and 3D operations
- Clearer distinction from `sketch` (which remains 2D only)
- Maintains backward compatibility via alias

**New Structure:**
```python
# Current
section(name='my_profile', plane='XY', at=(0, 0, 0))

# Enhanced
profile(name='my_profile', mode='2d', plane='XY', at=(0, 0, 0))  # 2D mode
profile(name='my_profile', mode='3d', at=(0, 0, 0))             # 3D mode
```

### 2. Decouple from Sketch Architecture

**Current Shared Components:**
- `_SectionProfile` class
- `PartProfileAdapter` / `SketcherProfileAdapter`
- Backend selection logic

**Proposed Decoupling:**
```python
# 2D Profile (current section functionality)
class Profile2D:
    def __init__(self, name, plane, at):
        self._profile = _SectionProfile2D()
        self._backend = PartSectionBackend()
    
    def circle(self, d=None, r=None, at=(0, 0)):
        # 2D circle in plane
        pass
    
    def pad(self, dist, dir='+'):
        # 2D → 3D via extrusion
        pass

# 3D Profile (new functionality)
class Profile3D:
    def __init__(self, name, at):
        self._profile = _SectionProfile3D()
        self._backend = PartSectionBackend()
    
    def circle3d(self, d=None, r=None, at=(0, 0, 0), normal=(0, 0, 1)):
        # 3D circle in any orientation
        pass
    
    def sweep3d(self, path_profile):
        # 2D profile along 3D path
        pass
```

### 3. 3D Path Creation Syntax

**3D Coordinate System:**
```python
# 3D coordinates
profile.to3d(x, y, z)
profile.to3d((x, y, z))

# 3D arcs
profile.arc3d(center=(cx, cy, cz), radius=r, start=(sx, sy, sz), end=(ex, ey, ez))
profile.arc3d(center=(cx, cy, cz), radius=r, start=(sx, sy, sz), end=(ex, ey, ez), normal=(nx, ny, nz))

# 3D lines
profile.line3d(x, y, z)
profile.line3d((x, y, z))

# 3D curves
profile.helix3d(radius, pitch, height, turns)
profile.spline3d([(x1, y1, z1), (x2, y2, z2), ...])
```

**3D Path Examples:**
```python
# Simple 3D path
path = profile(name='3d_path', mode='3d')
path.from_(0, 0, 0)
path.line3d(10, 0, 0)      # X direction
path.line3d(10, 10, 0)     # Y direction  
path.line3d(10, 10, 10)    # Z direction

# 3D arc path
path = profile(name='arc_path', mode='3d')
path.from_(0, 0, 0)
path.arc3d(center=(5, 0, 0), radius=5, start=(0, 0, 0), end=(10, 0, 0))

# Helical path
path = profile(name='helix_path', mode='3d')
path.helix3d(radius=5, pitch=2, height=20, turns=10)
```

### 4. Enhanced Sweep Operations

**Current Sweep:**
```python
# 2D profile + 2D path → 3D solid
profile.sweep(path_profile)
```

**Enhanced Sweep:**
```python
# 2D profile + 3D path → 3D solid
profile.sweep3d(path_profile)

# 3D profile + 3D path → 3D solid (future)
profile.sweep3d_full(path_profile)
```

**Sweep Examples:**
```python
# Create 2D profile
prof = profile(name='circle_profile', mode='2d', plane='XY')
prof.circle(r=2)

# Create 3D path
path = profile(name='3d_path', mode='3d')
path.from_(0, 0, 0)
path.line3d(10, 0, 0)
path.arc3d(center=(10, 5, 0), radius=5, start=(10, 0, 0), end=(20, 0, 0))
path.line3d(20, 0, 10)

# Sweep 2D profile along 3D path
result = prof.sweep3d(path)
```

### 5. Backward Compatibility

**Alias Support:**
```python
# Maintain existing API
section = profile  # Alias for backward compatibility

# Existing code continues to work
s = section(name='my_section', plane='XY')
s.circle(r=5)
s.pad(10)
```

**Mode Detection:**
```python
# Auto-detect mode based on usage
profile(name='auto_detect')
# If only 2D operations used → 2D mode
# If 3D operations used → 3D mode
```

### 6. Implementation Plan

**Phase 1: Decoupling**
- [ ] Create `_SectionProfile2D` and `_SectionProfile3D` classes
- [ ] Decouple shared geometry functions (arc calculation, etc.)
- [ ] Create separate adapters for 2D and 3D profiles
- [ ] Maintain existing `section` API via `profile` alias

**Phase 2: 3D Path Creation**
- [ ] Implement 3D coordinate system
- [ ] Add 3D primitives: `line3d()`, `arc3d()`, `helix3d()`
- [ ] Add 3D spline support
- [ ] Test 3D path creation

**Phase 3: Enhanced Sweep**
- [ ] Implement `sweep3d()` for 2D profile + 3D path
- [ ] Add profile orientation control along path
- [ ] Test complex 3D sweeps

**Phase 4: Advanced Features**
- [ ] 3D profile creation (3D shapes as profiles)
- [ ] Advanced path types (NURBS, etc.)
- [ ] Path editing and manipulation

### 7. Shared Components

**Common Geometry Functions:**
```python
# Shared utilities
class GeometryUtils:
    @staticmethod
    def calculate_arc(center, radius, start, end, direction):
        # Common arc calculation logic
        pass
    
    @staticmethod
    def normalize_vector(vec):
        # Common vector operations
        pass
    
    @staticmethod
    def rotate_point(point, center, axis, angle):
        # Common rotation logic
        pass
```

**Backend Abstraction:**
```python
class ProfileBackend:
    def pad(self, profile, dist, dir):
        pass
    
    def revolve(self, profile, angle_deg, axis):
        pass
    
    def sweep(self, profile, path_profile):
        pass
    
    def sweep3d(self, profile, path_profile):
        pass
```

### 8. Usage Examples

**2D Profile (current functionality):**
```python
# Traditional 2D profile
prof = profile(name='2d_profile', mode='2d', plane='XY')
prof.circle(r=5)
prof.pad(10)
```

**3D Path Creation:**
```python
# 3D path for complex geometry
path = profile(name='3d_path', mode='3d')
path.from_(0, 0, 0)
path.line3d(10, 0, 0)
path.arc3d(center=(10, 5, 0), radius=5, start=(10, 0, 0), end=(20, 0, 0))
path.helix3d(radius=3, pitch=1, height=10, turns=5)
```

**3D Sweep:**
```python
# 2D profile swept along 3D path
prof = profile(name='circle', mode='2d', plane='XY')
prof.circle(r=2)

path = profile(name='3d_path', mode='3d')
path.from_(0, 0, 0)
path.line3d(10, 0, 0)
path.arc3d(center=(10, 5, 0), radius=5, start=(10, 0, 0), end=(20, 0, 0))

result = prof.sweep3d(path)
```

### 9. Benefits

**Enhanced Capabilities:**
- Complex 3D paths (helixes, splines, arcs)
- More realistic modeling (pipes, cables, etc.)
- Advanced manufacturing (3D printing, CNC)

**Backward Compatibility:**
- Existing 2D code continues to work
- Gradual migration path
- No breaking changes

**Clear Separation:**
- `sketch`: 2D only, Sketcher-based
- `profile`: 2D/3D, Part-based
- Shared utilities for common operations

### 10. Future Considerations

**Advanced Features:**
- 3D profile creation (not just 2D profiles on 3D paths)
- Path editing and manipulation
- Advanced sweep options (twist, scale along path)
- Integration with FreeCAD's advanced features

**Performance:**
- Efficient 3D path storage
- Optimized sweep algorithms
- Memory management for complex paths

This strategy provides a clear path for enhancing the current 2D section functionality to support 3D operations while maintaining backward compatibility and clear separation of concerns.
