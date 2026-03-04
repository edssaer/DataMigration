const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const net = require('net');
const fs = require('fs');

// 保持对主窗口的引用
let mainWindow;
let serverProcess;
let logStream;

// 初始化日志文件
function initLog() {
  const logDir = app.isPackaged 
    ? path.join(path.dirname(app.getPath('exe')), 'logs')
    : path.join(__dirname, '..', 'logs');
  
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  
  const logFile = path.join(logDir, `app_${new Date().toISOString().replace(/:/g, '-')}.log`);
  logStream = fs.createWriteStream(logFile, { flags: 'a' });
  
  log('应用启动...');
  log('日志文件路径:', logFile);
  return logFile;
}

function log(...args) {
  const msg = args.join(' ');
  const timestamp = new Date().toISOString();
  const logMsg = `[${timestamp}] ${msg}`;
  console.log(logMsg);
  if (logStream) {
    logStream.write(logMsg + '\n');
  }
}

function logError(...args) {
  const msg = args.join(' ');
  const timestamp = new Date().toISOString();
  const logMsg = `[${timestamp}] ERROR: ${msg}`;
  console.error(logMsg);
  if (logStream) {
    logStream.write(logMsg + '\n');
  }
}

// 获取应用的基础目录
function getBaseDir() {
  if (app.isPackaged) {
    // 打包后的环境，使用 extraResources 目录
    const resourcesPath = process.resourcesPath;
    return path.join(resourcesPath, 'app');
  }
  // 开发环境
  return path.join(__dirname, '..');
}

// 检查端口是否被占用
function checkPort(port, callback) {
  const server = net.createServer();
  server.once('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      callback(true); // 端口被占用
    } else {
      callback(false);
    }
  });
  server.once('listening', () => {
    server.close();
    callback(false); // 端口可用
  });
  server.listen(port, 'localhost');
}

// 启动 Flask 服务器
function startServer() {
  return new Promise((resolve, reject) => {
    checkPort(5000, (isInUse) => {
      if (isInUse) {
        log('端口 5000 已被占用，可能已有服务器在运行');
        resolve();
        return;
      }

      const baseDir = getBaseDir();
      log('应用基础目录:', baseDir);
      log('打包状态:', app.isPackaged);

      // 检查 app.py 是否存在
      const appPyPath = path.join(baseDir, 'app.py');
      log('app.py 路径:', appPyPath);
      log('app.py 是否存在:', fs.existsSync(appPyPath));

      // 检查 index.html 是否存在
      const indexHtmlPath = path.join(baseDir, 'index.html');
      log('index.html 路径:', indexHtmlPath);
      log('index.html 是否存在:', fs.existsSync(indexHtmlPath));

      // 列出基础目录的文件
      log('基础目录文件列表:');
      try {
        const files = fs.readdirSync(baseDir);
        files.forEach(file => {
          log(' -', file);
        });
      } catch (e) {
        logError('读取目录失败:', e.message);
      }

      // 检查是否存在打包好的可执行文件
      const exePath = path.join(baseDir, 'data_migration_server.exe');
      log('可执行文件路径:', exePath);
      log('可执行文件是否存在:', fs.existsSync(exePath));
      
      // 启动 Flask 服务器
      if (fs.existsSync(exePath)) {
        // 使用打包好的可执行文件
        serverProcess = exec(`"${exePath}"`, {
          cwd: baseDir,
          env: {
            ...process.env
          }
        });
      } else {
        // 回退到使用 Python
        serverProcess = exec(`python "${appPyPath}"`, {
          cwd: baseDir,
          env: {
            ...process.env,
            PYTHONUNBUFFERED: '1'
          }
        });
      }

      serverProcess.stdout.on('data', (data) => {
        log('服务器输出:', data);
        if (data.includes('Running on http://')) {
          log('Flask 服务器启动成功');
          resolve();
        }
      });

      serverProcess.stderr.on('data', (data) => {
        logError('服务器错误:', data);
      });

      serverProcess.on('close', (code) => {
        log(`服务器进程退出，退出码 ${code}`);
      });

      // 给服务器一些启动时间
      setTimeout(resolve, 5000);
    });
  });
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: '数据库迁移工具',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false // 允许加载本地文件
    }
  });

  // 加载本地 Flask 服务器
  mainWindow.loadURL('http://localhost:5000');

  // 监听页面加载错误
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    logError('页面加载失败:', errorCode, errorDescription);
  });

  // 监听页面加载完成
  mainWindow.webContents.on('did-finish-load', () => {
    log('页面加载完成');
  });

  // 当窗口关闭时
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 处理新窗口打开
  mainWindow.webContents.on('new-window', (event, url) => {
    event.preventDefault();
    shell.openExternal(url);
  });
}

// 应用就绪时
app.whenReady().then(async () => {
  try {
    initLog();
    await startServer();
    createWindow();

    app.on('activate', function () {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  } catch (error) {
    logError('启动应用时出错:', error);
  }
});

// 关闭所有窗口时
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// 应用退出时
app.on('quit', function () {
  if (serverProcess) {
    serverProcess.kill();
  }
  if (logStream) {
    logStream.end();
  }
});
