const { spawn } = require('child_process')
const path = require('path')
const electron = require('electron')
const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE
const data = path.join(__dirname, 'user-data')
const child = spawn(electron, ['--no-sandbox', '--disable-gpu', '--disable-crash-reporter', '--disable-breakpad', '--user-data-dir=' + data, '.', ...process.argv.slice(2)], { stdio: 'inherit', env })
child.on('exit', code => process.exit(code ?? 0))
child.on('error', err => { console.error(err); process.exit(1) })
