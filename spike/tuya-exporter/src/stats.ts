import { Data } from "dataclass";
import { readFileSync } from 'fs';

const logger = require('pino')();


// ---- Some common utilities used for reshaping data. -------------------------

// Converts object to tuples of [prop name,prop type]
// So { a: 'Hello', b: 'World', c: '!!!' }
// will be  [a, 'Hello'] | [b, 'World'] | [c, '!!!']
type TuplesFromObject<T> = {
    [P in keyof T]: [P, T[P]]
}[keyof T];

// Gets all property  keys of a specified value type
// So GetKeyByValue<{ a: 'Hello', b: 'World', c: '!!!' }, 'Hello'> = 'a'
type GetKeyByValue<T, V> = TuplesFromObject<T> extends infer TT ?
    TT extends [infer P, V] ? P : never : never;


export const remap = <
    T extends { [key: string]: any },
    V extends string, // needed to force string literal types for mapping values
    U extends { [P in keyof T]: V }
>(original: T, mapping: U) => {
    const remapped: any = {};

    Object.keys(original).forEach(k => {
        if (k in mapping) {
            remapped[mapping[k]] = original[k];
        }
    });

    return remapped as {
        [P in U[keyof U]]: T[GetKeyByValue<U, P>] // Get the original type of the key in T by using GetKeyByValue to get to the original key
    };
};
// ----------------------------------------------------------------------------

// ---- Dataclass definitions -------------------------------------------------

export class PowerPlugStats extends Data {
    switch: Boolean = false;
    voltage_volts: number = 0;
    power_watts: number = 0;
    current_amps: number = 0;
    total_electricity_kwh: number = 0;

    static fromDatapoint(datapoint: {[key: string]: any}): PowerPlugStats  {
        // Datapoint ID to field mapping as defined by the Tuya IOT documentation
        // Ref: https://developer.tuya.com/en/docs/iot/product-standard-function-introduction?id=K9tp15ceh63gr

        // TODO: Make these datapoint values follow the specified units.
        let datapointFieldMapping = {
            '1': 'switch',
            '17': 'total_electricity_kwh',
            '18': 'current_amps',
            '19': 'power_watts',
            '20': 'voltage_volts'
        };

        const remappedFields = remap(datapoint, datapointFieldMapping);
        return PowerPlugStats.create(remappedFields);
    }
}

class PowerPlugConfig extends Data {
    id: string = '';
    key: string = '';
    ip: string = '';
};

export class Config extends Data {
    devices: PowerPlugConfig[] = [];

    static fromConfig(configPath: string): Config {
        let jsonData = readFileSync(configPath, 'utf-8');
        let jsonObj = JSON.parse(jsonData);

        return Config.create(jsonObj);
    }
}

// ----------------------------------------------------------------------------
