"""Exercise the Windows import path with generated geometry and texture pixels."""
import base64
import pathlib
import subprocess
import sys
import tempfile

from release_build import ROOT

sys.path.insert(0, str(ROOT / 'app'))
import core


def test(helper_dir):
    helper_dir = pathlib.Path(helper_dir).resolve()
    compiler = ROOT / 'tools/roslyn/tasks/net472/csc.exe'
    fixture = ROOT / 'tools/modeltool/NativeModelFixture.cs'
    with tempfile.TemporaryDirectory(prefix='pictoplus-native-test-') as folder:
        stage = pathlib.Path(folder)
        subprocess.run([str(compiler), '/nologo', '/r:SPICA.dll', '/r:System.Numerics.dll',
                        '/r:System.Drawing.dll', f'/out:{stage / "NativeModelFixture.exe"}', str(fixture)],
                       cwd=helper_dir, check=True)
        (stage / 'SPICA.dll').write_bytes((helper_dir / 'SPICA.dll').read_bytes())
        subprocess.run([str(stage / 'NativeModelFixture.exe')], cwd=stage, check=True)
        run_tool = core.run_tool

        def run_fixture_tool(name, *args):
            result = subprocess.run([str(helper_dir / name), *map(str, args)], capture_output=True,
                                    text=True, timeout=15)
            if result.returncode:
                raise ValueError(result.stderr)
            return result.stdout

        def read(*names):
            return core.read_native_model([base64.b64encode((stage / name).read_bytes()).decode()
                                           for name in names])

        core.run_tool = run_fixture_tool
        try:
            reference = read('embedded.bch')
            assert reference['meshes'][0] == dict(positions=[3,4,5,4,4,5,3,5,5],
                                                  uv=[.25,.75,.75,.75,.25,.25], material=0)
            assert reference['meshes'][1]['material'] == 1
            assert reference['materials'][0]['texture'] == 'test'
            assert reference['materials'][0]['transparent']
            assert reference['materials'][1]['texture'] is None
            assert read('model.bch', 'texture.gftexture') == reference
            assert read('model.bch', 'texture.bch') == reference
            assert read('texture.gftexture', 'model.bch')['modelIndex'] == 1
            assert read('model.bch')['missing'] == ['test']
            cgfx = read('embedded.bcres')
            assert cgfx['meshes'] == reference['meshes'][:1]
            assert cgfx['materials'] == reference['materials'][:1]
            assert cgfx['images'] == reference['images']
            assert read('model.bcres', 'texture.gftexture') == cgfx
            gf = read('model.gfmodel', 'texture.gftexture')
            assert gf['meshes'] == [dict(reference['meshes'][0], positions=[0,0,0,1,0,0,0,1,0])]
            assert gf['materials'] == cgfx['materials']
            assert gf['images'] == cgfx['images']
            for names, message in [
                (('texture.bch',), 'no model'),
                (('model.bch', 'model.bcres'), 'one model resource'),
            ]:
                try:
                    read(*names)
                except ValueError as error:
                    assert message in str(error), error
                else:
                    raise AssertionError(names)
            for data in (b'BCH\0' + b'\0' * 20, b'unknown format!!'):
                (stage / 'invalid.bin').write_bytes(data)
                try:
                    read('invalid.bin')
                except ValueError as error:
                    assert 'Could not import native model' in str(error), error
                else:
                    raise AssertionError('Accepted an invalid resource')
        finally:
            core.run_tool = run_tool


if __name__ == '__main__':
    test(sys.argv[1])
    print('Native model import checks passed')
