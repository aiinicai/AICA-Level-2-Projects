/**
 * launcher.js — Standalone Desktop Executable Launcher
 * Required by pkg to package Express server + SQLite database + built frontend into a single EXE.
 */

process.env.NODE_ENV = 'production';

// Import and run server
require('./server/server.js');
