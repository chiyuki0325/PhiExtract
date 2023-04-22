import sys
from pathlib import Path
import asyncio

from catalog import Catalog

import UnityPy
from UnityPy.enums import ClassIDType


async def extract_single_file(asset_file, filename_map, output_dir):
    if asset_file.name in filename_map:
        target_filename: str = filename_map[asset_file.name]
        with open(asset_file, 'rb') as f:
            env = UnityPy.load(f)

        if not target_filename.startswith('Assets/Tracks/'):
            return

        target_filename_parts = target_filename.split('/')
        output_file: Path = \
            output_dir / target_filename_parts[2].replace('.', ' - ', 1)[:-2] / target_filename_parts[3]
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.exists():
            print(f'{output_file} already exists, skipping ...')
            return

        print(f'Extracting {target_filename} to {output_file} ...')

        if target_filename.endswith('.json'):
            for obj in env.objects:
                if obj.type == ClassIDType.TextAsset:
                    with open(output_file, 'w') as f:
                        f.write(obj.read().text)
        elif target_filename.endswith('.wav'):
            for obj in env.objects:
                if obj.type == ClassIDType.AudioClip:
                    wav_data = list(obj.read().samples.values())[0]
                    with open(output_file, 'wb') as f:
                        f.write(wav_data)
                    ffmpeg_process = await asyncio.create_subprocess_exec(
                        'ffmpeg', '-y', '-i', output_file.__str__(), '-acodec', 'libvorbis',
                        output_file.with_suffix('.ogg').__str__()
                    )
                    await ffmpeg_process.wait()
                    output_file.unlink()
        elif target_filename.endswith('.png'):
            for obj in env.objects:
                if obj.type == ClassIDType.Texture2D:
                    with open(output_file, 'wb') as f:
                        obj.read().image.save(f)


async def main():
    assets_dir: Path = Path(sys.argv[1])
    output_dir: Path = Path(sys.argv[2])
    filename_map: dict[str, str] = Catalog(open(assets_dir / 'aa/catalog.json', 'r')).fname_map

    for file in (assets_dir / 'aa/Android').glob('*.bundle'):
        asyncio.create_task(extract_single_file(file, filename_map, output_dir))

    await asyncio.gather(*asyncio.all_tasks())


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python phi_extract.py <path to assets directory> <path to output directory>')
        exit()
    asyncio.run(main())
