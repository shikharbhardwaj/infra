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

# Last observed cumulative energy (aenergy.total, Wh) per device id. The Shelly
# keeps its own monotonic total; we mirror positive deltas into the Prometheus
# counter so `increase(smartplug_energy_watthour_total[...])` stays correct even
# with several plugs. Keyed by device - a single shared global previously made
# multiple plugs clobber each other's accounting.
last_energy_total: Dict[str, float] = {}

def observe_data(data: Dict, device_cfg: Device):
  required_keys = { 'apower', 'voltage', 'temperature', 'aenergy' }
  missing_keys = required_keys - data.keys()

  if missing_keys:
    log.warning('Did not find power data in response (missing: %s).', missing_keys)
    return

  labels = (device_cfg.id, device_cfg.friendly_name)

  power_watts = float(data.get('apower', 0))
  voltage_volts = float(data.get('voltage', 0))
  # Prefer the plug's own current reading; fall back to P/V only if the field
  # is absent (deriving it double-counts the power factor error).
  if data.get('current') is not None:
    current_amps = float(data['current'])
  else:
    current_amps = 0 if voltage_volts == 0 else power_watts / voltage_volts
  temp_celcius = data.get('temperature', {}).get('tC', 0)

  power.labels(*labels).set(power_watts)
  voltage.labels(*labels).set(voltage_volts)
  current.labels(*labels).set(current_amps)
  temp.labels(*labels).set(temp_celcius)
  switch_enabled.labels(*labels).set(1 if data.get('output') else 0)

  # Mirror the device's cumulative energy counter via per-device deltas.
  total_wh = float(data.get('aenergy', {}).get('total', 0))
  previous = last_energy_total.get(device_cfg.id)
  last_energy_total[device_cfg.id] = total_wh
  if previous is not None:
    # A drop means the device's counter reset (reboot) - count up from zero.
    delta = total_wh - previous if total_wh >= previous else total_wh
    if delta > 0:
      energy.labels(*labels).inc(delta)


async def observe_devices(device_configs: DeviceConfigs):
  log.info('Observing devices...')
  log.info(device_configs)


  while True:
    for cfg in device_configs.devices:
      try:
        resp = requests.get(f'http://{cfg.ip}/rpc/Switch.GetStatus?id={cfg.id}', auth=HTTPDigestAuth('admin', cfg.key), timeout=5)
      except requests.RequestException as e:
        log.warning('Request to %s (%s) failed: %s', cfg.friendly_name, cfg.ip, e)
        continue

      if not resp.ok:
        log.warning('Response not okay for %s: %d', cfg.friendly_name, resp.status_code)
        continue

      data = resp.json()
      log.debug('Received data from %s: %s', cfg.friendly_name, data)

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