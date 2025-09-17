def _orig_build_part(ctx):
    s = sketch(name='A', plane='XY', at=(0, 0, 0), visible=False)
    R = 5.0
    H = 10.0
    # Start at (R,0)
    s.from_(R, 0)
    # 1) Center+end (absolute): semicircle to (-R,0) ccw
    s.arc(radius=R, dir='ccw', centerAt=(0, 0), endAt=(-R, 0))
    # 2) Line down to (-R,-R), then line right to (R,-R)
    s.to(-R, -R)
    s.to(R, -R)
    # 3) R+E+dir: arc up to (R,0) with radius R, dir=ccw (center inferred)
    s.arc(radius=R, endAt=(R, 0), dir='ccw')
    s.close()
    # Pad and commit
    s.pad(H).add()


from pathlib import Path
def build_part(ctx):
    _orig_build_part(ctx)
    import bbcadam
    out = Path(__file__).with_suffix('.json')
    bbcadam.export('json', to=str(out))
