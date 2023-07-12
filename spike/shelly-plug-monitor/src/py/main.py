import asyncio
import dataclasses
import functools
import logging
import os
import signal

from typing import Dict, List

import dataclasses_json
import prometheus_client
import requests
from requests.auth import HTTPDigestAuth


LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
DEVICE_CONFIG_PATH = os.environ.get('DEVICE_CONFIG_PATH', '/usr/src/py/config.json')

logging.basicConfig(level=LOG_LEVEL, format='[%(levelname)8s] %(asctime)s %(filename)16s:L%(lineno)-3d %(funcName)16s() : %(message)s')

log = logging.getLogger(__name__)

@dataclasses_json.dataclass_json
@dataclasses.dataclass
class Device:
  id: str
  ip: str
  friendly_name: str
  key: str


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
temp = prometheus_client.Gauge('smartplug_temperature_celcius', 'Smartplug temperature (celcius)', ['device_id', 'device_name'])
energy = prometheus_client.Counter('smartplug_energy_watthour', 'Total energy consumption in Watthours', ['device_id', 'device_name'])

last_energy_captured = 0

def observe_data(data: Dict, device_cfg: Device):
  required_keys = { 'apower', 'voltage', 'temperature', 'aenergy' }
  missing_keys = required_keys - data.keys()

  if missing_keys:
    log.warning('Did not find power data in response.')
    return

  power_watts = float(data.get('apower', 0))
  voltage_volts = float(data.get('voltage', 0))
  current_amps = 0 if voltage_volts == 0 else power_watts / voltage_volts
  temp_celcius = data.get('temperature', {}).get('tC', 0)
  energy_by_minute_watt_hour = data.get('aenergy', {}).get('by_minute')[1] / 1000

  power.labels(device_cfg.id, device_cfg.friendly_name).set(power_watts)
  voltage.labels(device_cfg.id, device_cfg.friendly_name).set(voltage_volts)
  current.labels(device_cfg.id, device_cfg.friendly_name).set(current_amps)
  temp.labels(device_cfg.id, device_cfg.friendly_name).set(temp_celcius)

  global last_energy_captured
  if energy_by_minute_watt_hour != last_energy_captured:
    last_energy_captured = energy_by_minute_watt_hour
    energy.labels(device_cfg.id, device_cfg.friendly_name).inc(energy_by_minute_watt_hour)


async def observe_devices(device_configs: DeviceConfigs):
  log.info('Observing devices...')
  log.info(device_configs)


  while True:
    log.info('Observations, observations')

    for cfg in device_configs.devices:
      resp = requests.get(f'http://{cfg.ip}/rpc/Switch.GetStatus?id={cfg.id}', auth=HTTPDigestAuth('admin', cfg.key))
      if not resp.ok:
        log.warning('Response not okay: %d', resp.status_code)
        continue

      data = resp.json()

      log.info('Received data: %s', data)
      
      observe_data(data, cfg)

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