import { IncottMouseHID } from './mouse-hid.js';

const SYNC_REQUEST = Buffer.from([0x09, 0x06, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]);

function parseHeartbeat(data, mode) {
  if (data.length < 8) return null;

  const battery = data[1];
  const slot = ((data[2] >> 4) & 0x0F) + 1;
  
  const pollMap = { 0: 1000, 1: 500, 2: 250, 3: 125 };
  const polling = pollMap[data[2] & 0x0F] || '???';
  
  const debounce = data[3];

  // DPI calculation
  const multX = (data[4] & 0x0F) > 0 ? 5 : 1;
  const multY = (data[4] >> 4) > 0 ? 5 : 1;
  const dpiX = (data[5] + 1) * 50 * multX;
  const dpiY = (data[6] + 1) * 50 * multY;

  return {
    mode,
    battery,
    slot,
    dpiX,
    dpiY,
    pollingHz: polling,
    debounceMs: debounce
  };
}

function formatStatus(status) {
  if (!status) return null;
  
  return `[${status.mode}] | Bat: ${status.battery}% | ` +
         `Slot: ${status.slot} | DPI: ${status.dpiX}x${status.dpiY} | ` +
         `Poll: ${status.pollingHz}Hz | Debounce: ${status.debounceMs}ms`;
}

async function main() {
  const debug = process.argv.includes('--debug');
  
  console.log('🖱️  Incott G23V2SE Node.js Monitor');
  console.log(`Platform: ${process.platform}${debug ? ' (DEBUG mode)' : ''}\n`);

  const hid = new IncottMouseHID(debug);

  // Find device
  const deviceInfo = hid.findDevice();
  if (!deviceInfo) {
    console.error('❌ Mouse not found. Check USB connection.');
    process.exit(1);
  }

  console.log(`✅ Found device: ${deviceInfo.mode} (PID: 0x${deviceInfo.productId.toString(16).padStart(4, '0')})`);

  // Open device
  try {
    hid.open(deviceInfo.path);
    console.log('🔌 Connected. Requesting state...\n');
  } catch (err) {
    console.error(`❌ Failed to open device: ${err.message}`);
    process.exit(1);
  }

  let lastUpdate = Date.now();
  let printedFirst = false;

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n👋 Stopped.');
    hid.close();
    process.exit(0);
  });

  // Send initial sync request immediately
  try {
    hid.sendFeatureReport(SYNC_REQUEST);
    lastUpdate = Date.now();
  } catch (err) {
    console.error(`\n❌ Error sending initial sync: ${err.message}`);
    hid.close();
    process.exit(1);
  }

  // Main loop
  while (true) {
    // Periodic sync request (every 2 seconds)
    if (Date.now() - lastUpdate > 2000) {
      try {
        hid.sendFeatureReport(SYNC_REQUEST);
      } catch (err) {
        console.error(`\n❌ Error sending sync: ${err.message}`);
        break;
      }
      lastUpdate = Date.now();
    }

    // Read response
    try {
      const packet = await hid.read(64);
      
      if (debug) {
        console.log(`[Loop] Read ${packet.length} bytes, first byte: 0x${packet[0]?.toString(16) || 'empty'}`);
      }
      
      if (packet.length > 0 && packet[0] === 0x09) {
        const status = parseHeartbeat(packet, deviceInfo.mode);
        
        if (debug) {
          console.log(`[Loop] Parse result:`, status);
        }
        
        if (status) {
          const formatted = formatStatus(status);
          
          // Overwrite line for live updates
          if (printedFirst) {
            process.stdout.write('\r' + new Date(lastUpdate) + ' ' + formatted + '    ');
          } else {
            console.log();  // New line after "Requesting state..."
            process.stdout.write(new Date(lastUpdate) + ' ' + formatted + '    ');
            printedFirst = true;
          }
        }
      }
    } catch (err) {
      console.error(`\n❌ Error reading device: ${err.message}`);
      break;
    }

    // Small delay to avoid busy-waiting
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  hid.close();
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});