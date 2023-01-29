import asyncio
import dataclasses
import functools
import logging
import os
import signal

from typing import Dict, List

import dataclasses_json
import prometheus_client
import tinytuya

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
DEVICE_CONFIG_PATH = os.environ.get('DEVICE_CONFIG_PATH', '/usr/src/py/config.json')

logging.basicConfig(level=LOG_LEVEL, format='[%(levelname)8s] %(asctime)s %(filename)16s:L%(lineno)-3d %(funcName)16s() : %(message)s')

log = logging.getLogger(__name__)

@dataclasses_json.dataclass_json
@dataclasses.dataclass
class Device:
  key: str
  id: str
  ip: str
  friendly_name: str


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class DeviceConfigs:
  devices: List[Device]



def get_device_config():
  with open(DEVICE_CONFIG_PATH, 'r') as f:
    return DeviceConfigs.from_json(f.read())


switch_enabled = prometheus_client.Gauge('smartplug_enabled', 'Smartplug turned on or off', ['device_id', 'device_name'])
voltage = prometheus_client.Gauge('smartplug_voltage_volts', 'Smartplug voltage reading (volts)', ['device_id', 'device_name'])
current = prometheus_client.Gauge('smartplug_current_amps', 'Smartplug current reading (amperes)', ['device_id', 'device_name'])
power = prometheus_client.Gauge('smartplug_power_watts', 'Smartplug power reading (watts)', ['device_id', 'device_name'])

def observe_data(data: Dict, device_cfg: Device):
  if 'dps' not in data:
    log.warn('Did not find datapoints in data payload. Skipping observations')
    return
  
  dps = data['dps']

  if '18' in dps:
    current_amps_value = int(dps['18']) / 1000
    current.labels(device_cfg.id, device_cfg.friendly_name).set(current_amps_value)
  
  if '19' in dps:
    power_watts_value = int(dps['19']) / 10
    power.labels(device_cfg.id, device_cfg.friendly_name).set(power_watts_value)

  if '20' in dps:
    voltage_volts_value = int(dps['20']) / 10
    voltage.labels(device_cfg.id, device_cfg.friendly_name).set(voltage_volts_value)

async def observe_devices(device_configs: DeviceConfigs):
  log.info('Observing devices...')
  log.info(device_configs)

  devices = [(cfg, tinytuya.OutletDevice(dev_id=cfg.id, address=cfg.ip,
                                   local_key=cfg.key, version=3.3, persist=True))
             for cfg in device_configs.devices]

  # Initialize devices.
  for _, d in devices:
    payload = d.generate_payload(tinytuya.DP_QUERY)
    d.send(payload)

  while True:
    log.info('Observations, observations')

    for cfg, d in devices:
      data = d.receive()
      log.info('Received data: %s', data)
      
      observe_data(data, cfg)

      log.info('Sending heartbeat to: %s', cfg.friendly_name)
      payload = d.generate_payload(tinytuya.HEART_BEAT)
      d.send(payload)

      log.info('Send DPS Update Request to: %s', cfg.friendly_name)
      payload = d.generate_payload(tinytuya.UPDATEDPS, ['17', '18', '19', '20'])
      d.send(payload)

    await asyncio.sleep(5)
  


async def main():
  loop = asyncio.get_running_loop()


  def exit_handler(signal_name: str):
    log.info("Caught termination signal: %s", signal_name)
    loop.stop()


  for signame in ('SIGINT', 'SIGTERM', 'SIGQUIT'):
    loop.add_signal_handler(
        getattr(signal, signame), functools.partial(exit_handler, signame))
      
  log.info('Starting observations.')
  prometheus_client.start_http_server(9080)

  device_configs = get_device_config()
  await observe_devices(device_configs)

if __name__ == '__main__':
  asyncio.run(main())