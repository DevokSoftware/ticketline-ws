#!/usr/bin/env python3
"""
Setup script for ticketline-ws
Installs dependencies and sets up the environment
"""

import subprocess
import sys

def install_requirements():
    """Install required packages from requirements.txt"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Packages installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False
    return True

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("🌐 Installing Playwright browsers...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✅ Playwright browsers installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        return False
    return True

def main():
    print("🚀 Setting up ticketline-ws...")
    
    if not install_requirements():
        print("❌ Setup failed at package installation")
        return
    
    if not install_playwright_browsers():
        print("❌ Setup failed at browser installation")
        return
    
    print("\n✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Make sure PostgreSQL is running on localhost:5433")
    print("2. Ensure the 'giggz' database exists")
    print("3. Run: python ticketline-ws.py")

if __name__ == "__main__":
    main()