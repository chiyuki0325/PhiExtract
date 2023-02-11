import os
import sys
from pathlib import Path
from io import BytesIO
from threading import Thread
import asyncio
from aioshutil import make_archive, rmtree

from catalog import Catalog

import ffmpeg
import UnityPy
from UnityPy.enums import ClassIDType


def ffmpeg_writer(ffmpeg_proc, wav_bytes_arr):
    chunk_size = 1024
    n_chunks = len(wav_bytes_arr) // chunk_size
    remainder_size = len(wav_bytes_arr) % chunk_size
    for i in range(n_chunks):
        ffmpeg_proc.stdin.write(wav_bytes_arr[i * chunk_size:(i + 1) * chunk_size])
    if remainder_size > 0:
        ffmpeg_proc.stdin.write(wav_bytes_arr[chunk_size * n_chunks:])
    ffmpeg_proc.stdin.close()


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
                    ffmpeg_process = (
                        ffmpeg
                        .input('pipe:', format='wav')
                        .output('pipe:', format='ogg', acodec='libvorbis', loglevel='quiet')
                        .run_async(pipe_stdin=True, pipe_stdout=True)
                    )
                    output_stream = BytesIO()
                    ffmpeg_thread = Thread(
                        target=ffmpeg_writer,
                        args=(ffmpeg_process, wav_data)
                    )
                    ffmpeg_thread.start()
                    while ffmpeg_thread.is_alive():
                        output_chunk = ffmpeg_process.stdout.read(1024)
                        output_stream.write(output_chunk)
                    output_stream.seek(0)
                    await ffmpeg_process.wait()
                    with open(output_file.with_suffix('.ogg'), 'wb') as f:
                        f.write(output_stream.read())
        elif target_filename.endswith('.png'):
            for obj in env.objects:
                if obj.type == ClassIDType.Texture2D:
                    with open(output_file, 'wb') as f:
                        obj.read().image.save(f)


async def make_archive_single_folder(folder):
    print(f'Compressing {folder} ...')
    await make_archive(
        folder.absolute().__str__() + '.zip',
        'zip',
        folder
    )
    await rmtree(folder)


async def main():
    assets_dir: Path = Path(sys.argv[1])
    output_dir: Path = Path(sys.argv[2])
    filename_map: dict[str, str] = Catalog(open(assets_dir / 'aa/catalog.json', 'r')).fname_map

    for file in (assets_dir / 'aa/Android').glob('*.bundle'):
        asyncio.create_task(extract_single_file(file, filename_map, output_dir))

    await asyncio.gather(*asyncio.all_tasks())

    for folder in output_dir.glob('*'):
        asyncio.create_task(make_archive_single_folder(folder))

    await asyncio.gather(*asyncio.all_tasks())


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python phi_extract.py <path to assets directory> <path to output directory>')
        exit()
    asyncio.run(main())
