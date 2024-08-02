const fs = require('fs');
const path = require('path');
const Ajv2020 = require("ajv/dist/2020")

const ajv = new Ajv2020();
const schemaPath  = path.join(__dirname, 'service.schema.json');
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));

function validateConfigFile(filePath) {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const valid = ajv.validate(schema, data);
    if (!valid) {
        console.log(`Validation errors in ${filePath}:`);
        console.log(ajv.errors);
        process.exit(1);
    }
}

function findConfigFiles(dir) {
    const files = fs.readdirSync(dir);
    files.forEach(file => {
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            findConfigFiles(filePath);
        } else if (file === 'config.json') {
            validateConfigFile(filePath);
        }
    });
}
const deploymentDir = path.resolve(__dirname, '..');
findConfigFiles(deploymentDir);
