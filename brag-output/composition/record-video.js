const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function recordVideo() {
  const compositionPath = path.resolve(__dirname, 'index.html');
  const outputPath = path.resolve(__dirname, '..', 'brag.mp4');
  
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-web-security', '--allow-file-access-from-files']
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: path.dirname(outputPath), size: { width: 1920, height: 1080 } }
  });
  
  const page = await context.newPage();
  
  // Navigate to the composition
  await page.goto(`file://${compositionPath}`, { 
    waitUntil: 'networkidle',
    timeout: 60000 
  });
  
  // Wait for Hyperframes to initialize and animations to complete
  // The composition is 20 seconds at 30fps = 600 frames
  // Wait for the composition to finish (20 seconds + buffer)
  await page.waitForTimeout(22000);
  
  // Stop recording
  await context.close();
  await browser.close();
  
  // Find the recorded video file
  const videoFiles = fs.readdirSync(path.dirname(outputPath)).filter(f => f.endsWith('.webm'));
  if (videoFiles.length > 0) {
    const latestVideo = path.join(path.dirname(outputPath), videoFiles[videoFiles.length - 1]);
    fs.renameSync(latestVideo, outputPath.replace('.mp4', '.webm'));
    console.log(`Video saved to: ${outputPath.replace('.mp4', '.webm')}`);
  }
}

recordVideo().catch(console.error);