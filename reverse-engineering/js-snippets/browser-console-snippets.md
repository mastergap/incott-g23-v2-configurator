# Reverse engineering instructions

## Setup
- Use Google Chrome

- If you are on linux you need to let the browser to access your device:
    - You need to find out vendor id and device id of your mouse
    ```bash
    lsusb
    ```
    - create a udev rule
    ```bash
    sudo vim /etc/udev/rules.d/99-incott-mouse.rules
    ```
    - paste inside
    ```bash
    KERNEL=="hidraw*", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="xxxx", MODE="0666", TAG+="uaccess"
    ```
    - reload rules
    ```bash
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    ```
- Go to <https://incott.net/mouse/>
- Open the developer console
- Connect the device

## Inspect protocol messages
### Read messages sent by the mouse to the pc
Paste this js snippet in the browser's console
```javascript
(async () => {
  const devices = await navigator.hid.getDevices();
  if (devices.length === 0) {
    console.error("No HID devices found. Make sure the mouse is connected and you've granted permission.");
    return;
  }

  const myMouse = devices[0];
  
  // Open the device if it's closed
  if (!myMouse.opened) {
    await myMouse.open();
  }

  console.log("Connected to:", myMouse.productName);

  // Listen for data coming FROM the mouse
  myMouse.addEventListener('inputreport', event => {
    const { data, reportId } = event;
    console.log(`[IN] ID: ${reportId} | Hex:`, 
      Array.from(new Uint8Array(data.buffer))
      .map(b => b.toString(16).padStart(2, '0')).join(' ')
    );
  });

  // Intercept data being sent TO the mouse
  const originalSend = myMouse.sendReport.bind(myMouse);
  myMouse.sendReport = (reportId, data) => {
    console.log(`[OUT] ID: ${reportId} | Hex:`, 
      Array.from(new Uint8Array(data.buffer))
      .map(b => b.toString(16).padStart(2, '0')).join(' ')
    );
    return originalSend(reportId, data);
  };

  console.log("Listening for Incott packets...");
})();
```

### Read the messages sent by the pc to the mouse
Paste this js snippet in the browser's console
```javascript
(async () => {
  const [device] = await navigator.hid.getDevices();
  if (!device) return console.error("No device found");
  if (!device.opened) await device.open();

  console.log("Monitoring Feature Reports and Output Reports...");

  // Patch for standard Output Reports
  const originalSend = device.sendReport.bind(device);
  device.sendReport = (reportId, data) => {
    console.log(`[OUT-Standard] ID: ${reportId} | Hex:`, 
      Array.from(new Uint8Array(data.buffer)).map(b => b.toString(16).padStart(2, '0')).join(' '));
    return originalSend(reportId, data);
  };

  // Patch for Feature Reports (Likely what Incott uses)
  const originalFeature = device.sendFeatureReport.bind(device);
  device.sendFeatureReport = (reportId, data) => {
    console.log(`[OUT-Feature] ID: ${reportId} | Hex:`, 
      Array.from(new Uint8Array(data.buffer)).map(b => b.toString(16).padStart(2, '0')).join(' '));
    return originalFeature(reportId, data);
  };
})();
```