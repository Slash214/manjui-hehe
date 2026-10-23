import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', workers: 1, timeout: 60000, use: {
  baseURL: process.env.FRONTEND_URL ?? 'http://127.0.0.1:5173', channel: 'chrome', headless: true,
  screenshot: 'only-on-failure', trace: 'retain-on-failure',
}, reporter: [['list'], ['html', {open:'never'}]] });
