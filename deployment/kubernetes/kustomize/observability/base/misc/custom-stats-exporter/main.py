import asyncio
import collections
import logging
import os
import signal

import aiohttp
from prometheus_client import start_http_server, Info, Gauge

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')

def signal_handler(sig, frame):
    logging.info('Received termination signal: %s, exiting', sig)
    os._exit(0)

METRICS_PORT = int(os.getenv('METRICS_PORT', '9080'))
DISKINFO_REFRESH_INTERVAL_SECONDS = int(os.getenv('DISKINFO_REFRESH_INTERVAL_SECONDS', '10'))
TRUENAS_BASE_URL = os.getenv('TRUENAS_BASE_URL', None)
TRUENAS_API_TOKEN = os.getenv('TRUENAS_API_TOKEN', None)

if not TRUENAS_BASE_URL:
    logging.error('TRUENAS_BASE_URL environment variable is required')
    exit(1)

if not TRUENAS_API_TOKEN:
    logging.error('TRUENAS_API_TOKEN environment variable is required')
    exit(1)

last_diskinfo = collections.defaultdict(dict)

i = Gauge('truenas_disk_info', 'TrueNAS disk info', ['name', 'serial', 'model', 'size', 'description'])

async def main():
    try:
        # Fetch disk info from TrueNAS API.
        while True:
            async with aiohttp.ClientSession() as session:
                # Send a request to the TrueNAS API, with the auth token.
                async with session.get(f'{TRUENAS_BASE_URL}/api/v2.0/disk',
                                    headers={'Authorization': f'Bearer {TRUENAS_API_TOKEN}'}) as resp:
                    logging.info(f'Response status: {resp.status}')
                    if resp.status != 200:
                        logging.warning('Failed to fetch disk info, exiting')
                        return

                    try:
                        data = await resp.json()

                        # Diff against last diskinfo.
                        for disk in data:
                            disk_id = disk['identifier']
                            if disk_id not in last_diskinfo:
                                last_diskinfo[disk_id] = {}
                                for key, value in disk.items():
                                    if key in ['name', 'serial', 'model', 'size', 'description']:
                                        last_diskinfo[disk_id][key] = str(value)
                                logging.info(f'Adding disk {disk_id} to metrics, with values: {last_diskinfo[disk_id]}')
                                i.labels(**last_diskinfo[disk_id]).set(1)
                            else:
                                for key, value in disk.items():
                                        if key in ['name', 'serial', 'model', 'size', 'description'] and \
                                            last_diskinfo[disk_id].get(key) != str(value):
                                            logging.info(f'Disk {disk_id} {key} changed: {last_diskinfo[disk_id].get(key)} -> {value}, restarting')
                                            return


                    except Exception as e:
                        logging.exception(f'Failed to parse response: {e}')

            await asyncio.sleep(DISKINFO_REFRESH_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logging.info('Exiting main loop')

if __name__ == '__main__':
    # Start the server to expose the metrics.
    logging.info(f'Starting server on port {METRICS_PORT}')
    start_http_server(METRICS_PORT)

    # Start an asyncio event loop
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main())

    for signal in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)
    
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()