from pathlib import Path
from aioshutil import make_archive, rmtree
import asyncio
import sys


async def main():
    async def make_archive_single_folder(folder):
        print(f'Compressing {folder} ...')
        await make_archive(
            folder.absolute().__str__(),
            'zip',
            folder
        )
        await rmtree(folder)

    output_dir: Path = Path(sys.argv[1])
    for folder in output_dir.glob('*'):
        asyncio.create_task(make_archive_single_folder(folder))

    await asyncio.gather(*asyncio.all_tasks())


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python pack.py <path to output directory>')
        exit()
    asyncio.run(main())
