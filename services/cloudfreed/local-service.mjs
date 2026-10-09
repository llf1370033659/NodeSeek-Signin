import Server from './lib/Server.js';
const server = new Server({clientKey: process.env.CLOUDFREED_CLIENT_KEY, maxConcurrentTasks: 1, port: 3000, host: '127.0.0.1', timeout: 60});
let http;
let stopping = false;
async function stop() {
  if (stopping) return;
  stopping = true;
  for (const instance of server.instances) {
    if (typeof instance.Close === 'function') await instance.Close();
  }
  if (server.taskQueue) server.taskQueue.destroy();
  if (http) http.close();
  process.exit(0);
}
process.stdin.on('data', data => { if (data.toString().trim() === 'stop') stop(); });
process.stdin.on('end', stop);
try {
  await server.initialize();
  if (server.instances.some(instance => typeof instance.Solve !== 'function')) {
    throw new Error(server.instances.map(instance => instance.errormessage).filter(Boolean).join('; ') || 'Browser initialization failed');
  }
  server.app.get('/health', (_req, res) => res.json({ready: true}));
  http = server.listen();
} catch (error) {
  console.error(error.message);
  await stop();
}