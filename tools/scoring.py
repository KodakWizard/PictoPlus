"""Normal-puzzle scoring reconstructed from supplied ARM executable.

Core: 0x1a4640..0x1a4774, strike bonus: 0x24be80..0x24bf48.
These calculations are offline predictions until compared with further clears.
"""
import math,struct
def f32(n):return struct.unpack('<f',struct.pack('<f',n))[0]
def targets(record):
    assert len(record)==404
    return tuple(struct.unpack_from('<I',record,offset)[0] for offset in (368,376,400))
def calculate(time_targets,difficulty,seconds,mistakes=0):
    assert len(time_targets)==3 and all(t>0 for t in time_targets)
    index=('easy','medium','hard').index(difficulty)
    total=sum(time_targets);base=int(f32(f32(total)*f32(.006)))&65535
    target=time_targets[index]
    time_bonus=base if seconds<=target else int(max(0,f32(base-f32(f32((seconds-target)*base)/target))))
    allowance=min(20,math.ceil((total//3)/150)+3)
    maximum_mistake_bonus=int(f32(base*3.0))
    mistake_bonus=min(maximum_mistake_bonus,int(f32(f32(max(0,allowance-mistakes)*f32(base*3.0))/allowance)))
    multiplier=(f32(1.2),f32(1.5),f32(2.0))[index]
    points=int(f32(f32(f32(base*multiplier)+f32(time_bonus*multiplier))+f32(mistake_bonus*multiplier)))&65535
    return {'clear':base,'mistake_bonus':mistake_bonus,'time_bonus':time_bonus,
      'multiplier':multiplier,'points':points,'target_seconds':target,'mistake_allowance':allowance}
