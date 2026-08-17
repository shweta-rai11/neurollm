import type { CapacitorConfig } from '@capacitor/cli';

// Native (iOS/Android) wrapper around the same web app served at
// /Users/swetarai/AI_Brainnetwork/ai-brain/frontend. `webDir: 'dist'` means
// `npm run build` must be run (producing `dist/`) before `npx cap sync` --
// the native shell bundles that build, it does not talk to the Vite dev
// server. See MOBILE.md for the full build/run/deploy walkthrough,
// including how the app reaches the FastAPI backend from a real device.
const config: CapacitorConfig = {
  appId: 'com.neurollm.app',
  appName: 'NeuroLLM',
  webDir: 'dist',
};

export default config;
