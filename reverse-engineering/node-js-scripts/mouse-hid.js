import HID from 'node-hid';

const VID = 0x093a;
const PIDS = {
  0x622c: '⚡ Wired',
  0x522c: '📶 Wireless'
};

export class IncottMouseHID {
  constructor(debug = false) {
    this.device = null;
    this.path = null;
    this.debug = debug;
  }

  log(message) {
    if (this.debug) {
      console.log(`[DEBUG] ${message}`);
    }
  }

  findDevice() {
    const devices = HID.devices();
    this.log(`Found ${devices.length} total HID devices`);
    
    // Find ALL matching Incott mouse devices
    const matchingDevices = [];
    
    for (const dev of devices) {
      if (dev.vendorId === VID && PIDS[dev.productId]) {
        this.log(`Found Incott mouse: VID: 0x${dev.vendorId.toString(16).padStart(4, '0')}, PID: 0x${dev.productId.toString(16).padStart(4, '0')}, Path: ${dev.path}, Interface: ${dev.interface}`);
        matchingDevices.push(dev);
      }
    }
    
    if (matchingDevices.length === 0) {
      return null;
    }
    
    // Sort by interface number (ascending) and pick the HIGHEST one (management node)
    matchingDevices.sort((a, b) => (a.interface || 0) - (b.interface || 0));
    const selectedDevice = matchingDevices[matchingDevices.length - 1];
    
    this.log(`Selected device with interface ${selectedDevice.interface}: ${selectedDevice.path}`);
    
    return {
      path: selectedDevice.path,
      productId: selectedDevice.productId,
      mode: PIDS[selectedDevice.productId]
    };
  }

  open(devicePath) {
    try {
      this.device = new HID.HID(devicePath);
      this.path = devicePath;
    } catch (err) {
      throw new Error(`Failed to open device: ${err.message}`);
    }
  }

  sendFeatureReport(data) {
    if (!this.device) throw new Error('Device not opened');
    
    try {
      // Try sendFeatureReport first (preferred method)
      if (typeof this.device.sendFeatureReport === 'function') {
        this.log(`Using sendFeatureReport()`);
        const result = this.device.sendFeatureReport(Array.from(data));
        this.log(`Sent feature report: ${Array.from(data).map(x => '0x' + x.toString(16).padStart(2, '0')).join(' ')}`);
        return result;
      } else {
        // Fallback to write()
        this.log(`sendFeatureReport() not available, using write()`);
        const result = this.device.write(Array.from(data));
        this.log(`Wrote: ${Array.from(data).map(x => '0x' + x.toString(16).padStart(2, '0')).join(' ')}`);
        return result;
      }
    } catch (err) {
      throw new Error(`Failed to send feature report: ${err.message}`);
    }
  }

  read(size = 64) {
    if (!this.device) throw new Error('Device not opened');
    
    return new Promise((resolve) => {
      this.device.read((err, data) => {
        if (err) {
          this.log(`Read error (normal timeout): ${err.message}`);
          resolve(Buffer.alloc(0));
        } else if (data && data.length > 0) {
          this.log(`Read ${data.length} bytes: ${data.slice(0, 16).map(x => '0x' + x.toString(16).padStart(2, '0')).join(' ')}`);
          resolve(Buffer.from(data));
        } else {
          resolve(Buffer.alloc(0));
        }
      });
    });
  }

  close() {
    if (this.device) {
      try {
        this.device.close();
      } catch (err) {
        console.error('Error closing device:', err.message);
      }
      this.device = null;
    }
  }
}