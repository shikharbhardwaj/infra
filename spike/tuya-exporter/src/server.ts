import express from 'express';
import client from 'prom-client';
import pino from 'pino';

import {PowerPlugStats, Config} from './stats';

const logger = pino();
const server = express();
const register = client.register;

logger.info('Starting app')

server.get('/metrics', async (req: any, res: any) => {
	try {
		res.set('Content-Type', client.register.contentType);
		res.end(await register.metrics());
	} catch (ex) {
		res.status(500).end(ex);
	}
});


const port = process.env.PORT || 9080;
logger.info(
	`Server listening to ${port}, metrics exposed on /metrics endpoint`,
);

logger.info(PowerPlugStats.fromDatapoint({
  '1': true,
  '9': 0,
  '17': 100,
  '18': 944,
  '19': 2727,
  '20': 2438,
  '21': 1,
  '22': 522,
  '23': 13726,
  '24': 9311,
  '25': 4570,
  '26': 0,
  '38': 'memory',
  '39': false,
  '40': 'relay',
  '41': false,
  '42': '',
  '43': '',
  '44': ''
}));

logger.info(Config.fromConfig('/home/shikhar/dev/infra/spike/tuya-exporter/config.json'));

server.listen(port);