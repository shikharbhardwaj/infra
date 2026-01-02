#!/usr/bin/env python3
'''
arrange.py -- Arrange .mp4 files in the current folder into month-wise folders.
'''

import datetime
import os
from pathlib import Path
import platform
import re

import logging
from typing import Optional

logging.basicConfig(format='[%(levelname)8s] %(asctime)s %(filename)16s:L%(lineno)-3d %(funcName)16s() : %(message)s', level='INFO')

logger = logging.getLogger(__name__)

base_dir = Path(os.getcwd())
mp4_files = list(base_dir.glob('*.mp4'))
logging.info('Found %d mp4 files to arrange', len(mp4_files))

name_pat = re.compile(r'([^\d]+) ([\d]+)\.([\d]+)\..*')

def get_year_month(file: Path) -> Optional[str]:
    result = name_pat.match(file.name)

    if not result:
        logging.warning('Did not find expected file name pattern: %s, falling back to creation date.' % file.name)
        creation_date = get_creation_date(file)

        return f'{creation_date.year}-{creation_date.month:02d}'
    
    groups = result.groups()
    assert len(groups) == 3, "Did not find expected matches in file name"
    assert groups[0] == 'Counter-strike  Global Offensive'

    return f'{groups[1]}-{groups[2]}'

def get_creation_date(path_to_file) -> datetime.datetime:
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return datetime.datetime.fromtimestamp(os.path.getctime(path_to_file))
    else:
        stat = os.stat(path_to_file)
        try:
            return datetime.datetime.fromtimestamp(stat.st_birthtime)
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return datetime.datetime.fromtimestamp(stat.st_mtime)

for file in sorted(mp4_files):
    try:
        yyyy_mm = get_year_month(file)

        month_folder: Path = base_dir / yyyy_mm

        if not month_folder.exists():
            logging.info('Creating folder: %s', month_folder)
            month_folder.mkdir()

        os.rename(file, month_folder / file.name)
    except:
        logger.exception('Could not convert file: %s', file)
