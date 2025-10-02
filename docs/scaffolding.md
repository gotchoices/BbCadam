# Project Scaffolding Guide

This guide covers creating a complete BbCadam project structure. For basic installation and quick start, see the [main README](../README.md#quick-start).

## Complete Project Setup

```bash
# Create project and install BbCadam (see main README for details)
mkdir myproject && cd myproject
python -m venv .venv && source .venv/bin/activate
pip install git+https://github.com/gotchoices/BbCadam.git

# Create full directory structure
mkdir -p {config,specs/{parts,assemblies},build/{parts,assemblies},exports/{step,stl}/{parts,assemblies}}
```

## Configuration Files

### Project Settings (`config/settings.yaml`)

```yaml
# Project-wide settings
units: mm  # or 'in' for inches
exports:
  step: true
  stl: true
```

### Project Parameters (`config/params.yaml`)

```yaml
# Project-wide parameter defaults
material_thickness: 3.0
standard_radius: 5.0
```

### Part Parameters (`specs/parts/<partname>/params.yaml`)

```yaml
# Part-specific parameters (override project defaults)
width: 50
height: 30
depth: 10
```

## Template Files

### Basic Part (`specs/parts/demo/demo.py`)

```python
def build_part(ctx):
    # Get parameters (see api.md for param system details)
    width = param('width', 20)
    height = param('height', 10) 
    depth = param('depth', 5)
    
    # Create geometry
    box(width, height, depth).add()
    
    # Export (optional - can use CLI --export instead)
    export(['step', 'stl'])
```

### Basic Assembly (`specs/assemblies/demo/demo.py`)

```python
def build_assembly(ctx):
    # Link to parts
    component('../parts/demo/demo.py', 'base').add()
    component('../parts/demo/demo.py', 'top').at(0, 0, 20).add()
```

## Parameter System

For complete parameter documentation, see [api.md](api.md#parameters). Key points:

- **Hierarchy**: part params → project params → defaults
- **Types**: numeric, string, expressions (`"=width*2"`)
- **Usage**: `param('name', default_value)`

## CLI Usage

See [main README](../README.md#cli-tools) for CLI documentation. Common commands:

```bash
# Build single part
bbcadam-build specs/parts/demo/demo.py --export step stl

# Launch watcher
bbcadam-launch --project .

# Debug geometry
bbcadam-dump specs/parts/demo/demo.py
```

## Directory Structure Reference

```
myproject/
├── config/
│   ├── settings.yaml      # Project settings
│   └── params.yaml        # Project parameter defaults
├── specs/
│   ├── parts/
│   │   └── <partname>/
│   │       ├── <partname>.py    # Part script
│   │       └── params.yaml      # Part parameters (optional)
│   └── assemblies/
│       └── <asmname>/
│           ├── <asmname>.py     # Assembly script  
│           └── params.yaml      # Assembly parameters (optional)
├── build/                 # Generated FreeCAD files
│   ├── parts/
│   └── assemblies/
└── exports/               # Exported files
    ├── step/
    │   ├── parts/
    │   └── assemblies/
    └── stl/
        ├── parts/
        └── assemblies/
```

This structure enables the CLI tools to auto-detect project layout and parameter files.
