#!/usr/bin/env python3
"""
Test script for local system hardware discovery.
"""

import asyncio
import json

async def test_local_hardware_discovery():
    """Test local hardware discovery capabilities."""
    print("🔧 Testing Local System Hardware Discovery\n")
    print("=" * 60)
    
    try:
        import platform
        if platform.system() == "Darwin":
            from src.tools.macos_hardware_discovery import MacOSHardwareDiscovery
            discovery = MacOSHardwareDiscovery()
        else:
            from src.tools.system_hardware_discovery import SystemHardwareDiscovery
            discovery = SystemHardwareDiscovery()
        hardware = await discovery.discover_all_hardware()
        
        print(f"🖥️  **System**: {hardware.hostname}")
        print(f"📍 **Distribution**: {hardware.distribution}")
        print(f"🔨 **Kernel**: {hardware.kernel}")
        print(f"⏰ **Uptime**: {hardware.uptime_hours:.1f} hours\n")
        
        # CPU Information
        if hardware.cpu:
            cpu = hardware.cpu
            print("🔧 **CPU Information**")
            print(f"   Model: {cpu.model}")
            print(f"   Architecture: {cpu.architecture}")
            print(f"   Cores: {cpu.cores}, Threads: {cpu.threads}")
            print(f"   Max Frequency: {cpu.frequency_mhz:.0f} MHz")
            if cpu.cache_l3_kb:
                print(f"   L3 Cache: {cpu.cache_l3_kb} KB")
            print()
        
        # Memory Information
        if hardware.memory:
            mem = hardware.memory
            print("💾 **Memory Information**")
            print(f"   Total: {mem.total_gb:.1f} GB")
            print(f"   Used: {mem.used_gb:.1f} GB ({mem.used_gb/mem.total_gb*100:.1f}%)")
            print(f"   Available: {mem.available_gb:.1f} GB")
            if mem.swap_total_gb > 0:
                print(f"   Swap: {mem.swap_used_gb:.1f}/{mem.swap_total_gb:.1f} GB")
            print()
        
        # Storage Information
        if hardware.storage:
            print("💽 **Storage Devices**")
            for storage in hardware.storage:
                print(f"   {storage.device} ({storage.type})")
                print(f"     Model: {storage.model}")
                print(f"     Size: {storage.size_gb:.1f} GB")
                if storage.mount_point:
                    print(f"     Mounted: {storage.mount_point} ({storage.filesystem})")
                    usage_pct = (storage.used_gb / storage.size_gb * 100) if storage.size_gb > 0 else 0
                    print(f"     Used: {storage.used_gb:.1f}/{storage.size_gb:.1f} GB ({usage_pct:.1f}%)")
            print()
        
        # Network Information
        if hardware.network:
            print("🌐 **Network Interfaces**")
            for net in hardware.network:
                print(f"   {net.interface} ({net.status})")
                if net.ip_addresses:
                    print(f"     IP: {', '.join(net.ip_addresses)}")
                print(f"     MAC: {net.mac_address}")
                if net.speed_mbps:
                    print(f"     Speed: {net.speed_mbps} Mbps")
            print()
        
        # GPU Information
        if hardware.gpus:
            print("🎮 **GPU Devices**")
            for gpu in hardware.gpus:
                print(f"   {gpu.pci_id}: {gpu.model}")
                if gpu.driver:
                    print(f"     Driver: {gpu.driver}")
                if gpu.memory_gb:
                    print(f"     Memory: {gpu.memory_gb:.1f} GB")
            print()
        else:
            print("🎮 **GPU Devices**: No GPU detected or lspci not available\n")
        
        print("=" * 60)
        print("✅ Local hardware discovery completed successfully!")
        
        # Test summary function
        print("\n📊 **Resource Summary Test**")
        print("-" * 30)
        
        if hardware.cpu and hardware.memory:
            print(f"System: {hardware.hostname} ({hardware.distribution})")
            print(f"CPU: {hardware.cpu.cores} cores, {hardware.cpu.threads} threads")
            print(f"Memory: {hardware.memory.used_gb:.1f}/{hardware.memory.total_gb:.1f} GB ({hardware.memory.used_gb/hardware.memory.total_gb*100:.1f}% used)")
            
            total_storage = sum(s.size_gb for s in hardware.storage)
            if total_storage > 0:
                print(f"Storage: {total_storage:.1f} GB total across {len(hardware.storage)} devices")
            
            if hardware.gpus:
                print(f"GPUs: {len(hardware.gpus)} device(s)")
        
        print("\n🎯 **Use Cases for Pi/Edge Deployment**:")
        print("- Portable network admin tool with full hardware visibility")
        print("- Corporate test lab resource management")
        print("- Edge infrastructure monitoring and optimization")
        print("- Development environment resource tracking")
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
    except Exception as e:
        print(f"❌ Hardware discovery failed: {e}")

async def test_available_commands():
    """Test what system commands are available."""
    print("\n🔍 Testing Available System Commands\n")
    print("-" * 40)
    
    import subprocess
    
    commands_to_test = [
        "lscpu",
        "lsblk", 
        "lspci",
        "ip",
        "df",
        "cat /proc/meminfo",
        "cat /proc/cpuinfo",
        "nvidia-smi"
    ]
    
    for cmd in commands_to_test:
        try:
            cmd_parts = cmd.split()
            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {cmd}: Available")
            else:
                print(f"❌ {cmd}: Failed ({result.returncode})")
        except FileNotFoundError:
            print(f"❌ {cmd}: Not found")
        except subprocess.TimeoutExpired:
            print(f"⏰ {cmd}: Timeout")
        except Exception as e:
            print(f"❌ {cmd}: Error - {e}")

async def main():
    """Run all tests."""
    await test_available_commands()
    await test_local_hardware_discovery()

if __name__ == "__main__":
    asyncio.run(main())