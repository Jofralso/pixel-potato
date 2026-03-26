# Client Setup by Operating System 🖥️

Platform-specific instructions for connecting to PixelPotato from different machines.

---

## 🍎 macOS Setup

### Prerequisites
- Python 3.8+ (check: `python3 --version`)
- Git
- Terminal (built-in)

### Installation

**1. Install Python (if needed)**
```bash
# Using Homebrew (recommended)
brew install python3

# Verify installation
python3 --version
```

**2. Clone PixelPotato repository**
```bash
git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato
```

**3. Create virtual environment** (recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```

**4. Install dependencies**
```bash
pip install websockets
```

### Running the Client

**Find server IP address:**
```bash
# If server is on your network, ask the server to run:
hostname -I  # on the server machine

# Example output: 192.168.1.100

# Or check your own IP:
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Connect to PixelPotato:**
```bash
# Interactive mode
python3 clients/network_client.py --host 192.168.1.100 --port 8000

# Single message mode
python3 clients/network_client.py \
  --host 192.168.1.100 \
  --message "Write a Python function to reverse a string"
```

### Using in VS Code (with Claude Code)

**1. Install extensions**
- VS Code
- Claude Code (by Anthropic)
- Python extension

**2. Setup in VS Code**
```bash
# Open VS Code in pixel-potato directory
code .

# In VS Code terminal (Cmd+`)
source venv/bin/activate
python3 clients/network_client.py --host 192.168.1.100 --port 8000
```

**3. Use both simultaneously**
- Claude Code chat in VS Code sidebar
- PixelPotato terminal for file operations
- Copy results between them

### macOS Firewall

If connection is refused:

```bash
# Check firewall status
sudo /usr/libexec/ApplicationFirewall/socketfilterfw -getglobalstate

# Allow Python (if needed)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw -setglobalstate off
# Or add exception for specific port
```

### Aliases (Optional - Make it Easier)

Add to `~/.zshrc` or `~/.bash_profile`:

```bash
alias potato='python3 ~/pixel-potato/clients/network_client.py'
alias potato-mac='source ~/pixel-potato/venv/bin/activate && python3 ~/pixel-potato/clients/network_client.py'
```

Then restart terminal and use:
```bash
potato --host 192.168.1.100 --port 8000
```

---

## 🪟 Windows 10/11 Setup

### Prerequisites
- WSL2 (Windows Subsystem for Linux 2) - Recommended
- Or: Native Windows Python + Git

### Option A: WSL2 (Recommended for Developers)

**1. Enable WSL2**
```powershell
# In PowerShell (Administrator)
wsl --install
# Restart computer
wsl --set-default-version 2
```

**2. Install Ubuntu in WSL2**
```powershell
wsl --install -d Ubuntu-22.04
# Wait for Ubuntu to install and restart
```

**3. Setup in WSL2 terminal**
```bash
# Update package manager
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3 python3-venv python3-pip git -y

# Clone repository
git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install websockets
```

**4. Connect to server**
```bash
# Find server IP (ask server to run this on their machine)
hostname -I

# Connect to PixelPotato
python3 clients/network_client.py --host 192.168.1.100 --port 8000
```

### Option B: Native Windows Python

**1. Download and install Python**
- Go to [python.org](https://python.org)
- Download Python 3.11+
- **Important:** Check "Add Python to PATH" during installation

**2. Install Git**
- Go to [git-scm.com](https://git-scm.com)
- Download and install Git Bash

**3. Clone and setup**
```cmd
# Open Command Prompt or Git Bash
git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato

# Create virtual environment
python -m venv venv

# Activate virtual environment
# For Command Prompt:
venv\Scripts\activate
# For PowerShell:
venv\Scripts\Activate.ps1

# Install dependencies
pip install websockets
```

**4. Run the client**
```cmd
python clients/network_client.py --host 192.168.1.100 --port 8000
```

### Windows Firewall

If connection is refused:

```powershell
# Allow through firewall (PowerShell - Administrator)
New-NetFirewallRule -DisplayName "PixelPotato" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000

# Or disable specific to network
Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private
```

### Using in VS Code (Windows)

**1. Install VS Code + extensions**
- [VS Code](https://code.visualstudio.com)
- Claude Code extension
- Python extension

**2. Open folder**
```powershell
cd pixel-potato
code .
```

**3. In VS Code terminal**
```powershell
# Activate venv
venv\Scripts\Activate.ps1

# Run client
python clients/network_client.py --host 192.168.1.100 --port 8000
```

### Create Batch Shortcut (Windows)

Create `potato.bat` in pixel-potato folder:

```batch
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python clients/network_client.py %*
```

Then use:
```cmd
potato.bat --host 192.168.1.100 --port 8000
```

---

## 🐧 Linux Setup

### Prerequisites
- Python 3.8+
- Git
- curl or wget

### Debian/Ubuntu

**1. Install dependencies**
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git -y
```

**2. Clone repository**
```bash
git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato
```

**3. Setup virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**4. Install Python packages**
```bash
pip install --upgrade pip
pip install websockets
```

**5. Connect to server**
```bash
python3 clients/network_client.py --host 192.168.1.100 --port 8000
```

### Fedora/RHEL/CentOS

```bash
sudo dnf install python3 python3-venv git -y

git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato

python3 -m venv venv
source venv/bin/activate

pip install websockets
python3 clients/network_client.py --host 192.168.1.100 --port 8000
```

### Arch Linux

```bash
sudo pacman -S python git

git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato

python -m venv venv
source venv/bin/activate

pip install websockets
python clients/network_client.py --host 192.168.1.100 --port 8000
```

### Firewall (UFW - Ubuntu/Debian)

```bash
# Allow port 8000 (if connecting through firewall)
sudo ufw allow 8000

# Check firewall status
sudo ufw status
```

### Create Shell Alias (Linux)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias potato='~/pixel-potato/venv/bin/python3 ~/pixel-potato/clients/network_client.py'
```

Then:
```bash
source ~/.bashrc
potato --host 192.168.1.100 --port 8000
```

---

## 🔗 Finding the Server IP

### On the Server Machine

**macOS:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
# Look for 192.168.x.x or 10.x.x.x
```

**Windows (PowerShell):**
```powershell
ipconfig
# Look for "IPv4 Address" (non-127.0.0.1)
```

**Windows (WSL2):**
```bash
hostname -I
# or check Windows IP and use that
ipconfig  # from Windows PowerShell
```

**Linux:**
```bash
hostname -I
# or
ip addr show
# Look for inet 192.168.x.x or 10.x.x.x
```

### Quick Test: Is the Server Reachable?

**macOS/Linux:**
```bash
ping 192.168.1.100
telnet 192.168.1.100 8000
```

**Windows (PowerShell):**
```powershell
Test-NetConnection -ComputerName 192.168.1.100 -Port 8000
```

---

## Usage Examples

### macOS Example

```bash
$ python3 clients/network_client.py --host 192.168.1.100 --port 8000

🥔 Connecting to 192.168.1.100:8000...
✅ Connected! Session: a1b2c3d4
Type messages. Press Ctrl+C to exit.

You: Analyze my Python code for performance issues
🥔 [streams analysis]...

You: Show me the top 3 optimizations
🥔 Here are the most impactful optimizations...

You: /quit
Goodbye! 🥔
```

### Windows PowerShell Example

```powershell
PS> python clients/network_client.py --host 192.168.1.100 --port 8000

🥔 Connecting to 192.168.1.100:8000...
✅ Connected! Session: a1b2c3d4
Type messages. Press Ctrl+C to exit.

You: What Python version is recommended?
🥔 Python 3.11+ is recommended for...

You: /quit
```

### Linux Terminal Example

```bash
$ python3 clients/network_client.py --host 192.168.1.100 --port 8000

🥔 Connecting to 192.168.1.100:8000...
✅ Connected! Session: a1b2c3d4

You: Find all TODO comments in the project
🥔 Searching through files...
  - src/main.py:42 - TODO: Add error handling
  - src/utils.py:15 - TODO: Optimize loop

You: /quit
```

---

## Integration with VS Code (All Platforms)

### macOS & Linux

**1. Install VS Code**
- Download from [code.visualstudio.com](https://code.visualstudio.com)

**2. Install extensions**
- Claude Code (by Anthropic)
- Python

**3. Create VS Code task**
Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start PixelPotato Client",
      "type": "shell",
      "command": "source ${workspaceFolder}/venv/bin/activate && python3 ${workspaceFolder}/clients/network_client.py",
      "args": ["--host", "192.168.1.100", "--port", "8000"],
      "isBackground": false,
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": true,
        "panel": "new"
      }
    }
  ]
}
```

Then run with `Cmd+Shift+B` (macOS) or `Ctrl+Shift+B` (Linux)

### Windows

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start PixelPotato Client",
      "type": "shell",
      "command": "${workspaceFolder}\\venv\\Scripts\\activate.bat && python ${workspaceFolder}\\clients\\network_client.py",
      "args": ["--host", "192.168.1.100", "--port", "8000"],
      "isBackground": false,
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": true,
        "panel": "new"
      }
    }
  ]
}
```

---

## Troubleshooting by OS

### macOS Issues

**"Command not found: python3"**
```bash
brew install python3
```

**"Permission denied"**
```bash
chmod +x clients/network_client.py
```

**WSL2 interop needed (if running from Windows side)**
```bash
# Run from WSL terminal instead
wsl python3 clients/network_client.py --host 192.168.1.100
```

### Windows Issues

**"'python' is not recognized"**
- Reinstall Python and check "Add Python to PATH"
- Restart terminal/VS Code

**"Module not found: websockets"**
```cmd
pip install --upgrade pip
pip install websockets
```

**"Connection refused" in WSL2**
- Use Windows IP (from `ipconfig`), not WSL IP
- Or use `localhost:8000` if both are on same machine

### Linux Issues

**"Permission denied: /dev/pts/0"**
```bash
stty sane
```

**Port already in use**
```bash
lsof -i :8000  # Find what's using port 8000
```

**Firewall blocking**
```bash
sudo ufw allow 8000
sudo systemctl restart ufw
```

---

## See Also

- [MULTI_USER.md](MULTI_USER.md) — Detailed network setup
- [CLAUDE_CODE.md](CLAUDE_CODE.md) — VS Code integration
- [README.md](../README.md) — Main documentation
