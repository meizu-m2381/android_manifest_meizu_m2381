"""Prepare narrowly scoped SurfaceFlinger startup and graphics-backend trials."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous-round', type=int, required=True)
    parser.add_argument('--round', type=int, required=True)
    args = parser.parse_args()
    old, new = args.previous_round, args.round
    assert (old, new) in [(39, 40), (40, 41), (41, 42), (43, 44)]
    names = [f'init.round{old}.rc', f'init.staged-round{old}.rc',
             f'watch.round{old}.sh', f'kmsg-wrapper.round{old}.sh',
             f'prepare-adb.round{old}.sh', f'checkpoint.round{old}.sh',
             f'modules.blocklist.round{old}', f'vendor-modprobe.round{old}.sh',
             f'bootdiag-deadline.round{old}', f'recover-adb-parent.round{old}.sh']
    contents = {name.replace(f'round{old}', f'round{new}'):
                (args.previous / name).read_bytes()
                .replace(f'round{old}'.encode(), f'round{new}'.encode())
                .replace(f'BOOTDIAG{old}'.encode(), f'BOOTDIAG{new}'.encode())
                for name in names}
    entry = f'init.round{new}.rc'
    text = contents[entry].decode('utf-8')
    marker = 'on early-init\n'
    assert text.count(marker) >= 1
    if new == 40:
        setting = '    setprop service.sf.prime_shader_cache false\n'
        change = 'set service.sf.prime_shader_cache=false before SurfaceFlinger starts'
        evidence = 'round39 SIGABRT in Skia primeCache validate_backend_texture'
    elif new == 41:
        assert text.count('    setprop service.sf.prime_shader_cache false\n') == 1
        setting = '    setprop debug.renderengine.backend skiavkthreaded\n'
        change = 'select threaded Skia Vulkan; retain disabled shader-cache priming'
        evidence = 'round40 same Ganesh texture assertion during actual composition with priming disabled'
    elif new == 42:
        assert text.count('    setprop debug.renderengine.backend skiavkthreaded\n') == 1
        assert text.count('    setprop service.sf.prime_shader_cache false\n') == 1
        setting = ''
        change = 'retain Vulkan backend; separately rebuild vendor with ARM64 mapper getStub fix'
        evidence = 'round41 Vulkan driver casts BsMapper to IQtiMapper and calls vtable+0xf0'
    else:
        assert text.count('    setprop debug.renderengine.backend skiavkthreaded\n') == 1
        setting = '    setprop debug.hwui.renderer skiavk\n'
        change = 'select Vulkan HWUI for application and system_server RenderThreads'
        evidence = 'round43 system_server, SystemUI and setup wizard SIGSEGV in SkiaOpenGLPipeline renderFrame'
    if setting:
        assert setting not in text
        text = text.replace(marker, marker + setting, 1)
    contents[entry] = text.encode('utf-8')
    args.output.mkdir(exist_ok=False)
    for name, data in contents.items():
        (args.output / name).write_bytes(data)
    (args.output / 'plan.json').write_text(json.dumps({
        'previous_round': old, 'round': new,
        'change': change,
        'evidence': evidence,
        'retained': 'deferred ADB, exact misc recovery, normal encryption, tz_log blocklist, C4 isolation',
        'userdata': 'normal Android mount; no wipe, format or encryption bypass',
        'limitation': 'successful boot would not yet prove all display paths or hardware services',
    }, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
