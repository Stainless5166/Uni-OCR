import platform
import psutil
import time
import socket
import subprocess
import re
from importlib.metadata import version, PackageNotFoundError
from fastapi import APIRouter, Depends
from .routers_auth import get_current_user

router = APIRouter(prefix="/api/system", tags=["System"])

def get_cpu_model():
    sys_os = platform.system()
    if sys_os == "Darwin":
        try:
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        except Exception:
            return "Unknown Apple CPU"
    elif sys_os == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"

def get_gpu_info():
    sys_os = platform.system()
    if sys_os == "Darwin":
        try:
            out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True)
            match = re.search(r"Chipset Model:\s*(.*)", out)
            cores = re.search(r"Total Number of Cores:\s*(\d+)", out)
            if match:
                name = match.group(1).strip()
                if cores:
                    name += f" ({cores.group(1).strip()} Cores)"
                return name
        except Exception:
            pass
    elif sys_os == "Linux":
        try:
            out = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True)
            return out.strip().split('\n')[0]
        except Exception:
            pass
    return "No Dedicated GPU / Unknown"

def get_gpu_percent():
    sys_os = platform.system()
    if sys_os == "Darwin":
        try:
            out = subprocess.check_output(["ioreg", "-l", "-w", "0"], text=True)
            match = re.search(r"\"Device Utilization %\"=(\d+)", out)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    elif sys_os == "Linux":
        try:
            out = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], text=True)
            return int(out.strip().split('\n')[0])
        except Exception:
            pass
    return 0

@router.get("/info", dependencies=[Depends(get_current_user)])
def get_system_info():
    vmem = psutil.virtual_memory()
    mem_total_gb = vmem.total / (1024**3)
    mem_used_gb = (vmem.total - vmem.available) / (1024**3)
    
    # Disk usage (calculate used based on free space for better accuracy on macOS)
    disk_usage = psutil.disk_usage('/')
    disk_total_gb = disk_usage.total / (1024**3)
    disk_free_gb = disk_usage.free / (1024**3)
    disk_used_gb = disk_total_gb - disk_free_gb
    
    swap = psutil.swap_memory()
    
    try:
        uni_ver = version("uniocr")
    except PackageNotFoundError:
        uni_ver = "3.0.1" # Fallback

    info = {
        "uniocr_version": uni_ver,
        "os": platform.system(),
        "release": platform.release(),
        "arch": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_model": get_cpu_model(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_total_gb": round(mem_total_gb, 2),
        "memory_used_gb": round(mem_used_gb, 2),
        "memory_used_percent": round((mem_used_gb / mem_total_gb) * 100, 1) if mem_total_gb > 0 else 0,
        "disk_total_gb": round(disk_total_gb, 2),
        "disk_used_gb": round(disk_used_gb, 2),
        "disk_used_percent": round((disk_used_gb / disk_total_gb) * 100, 1) if disk_total_gb > 0 else 0,
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_percent": swap.percent,
        "gpu_model": get_gpu_info(),
        "gpu_percent": get_gpu_percent(),
        "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1),
        "network_ip": socket.gethostbyname(socket.gethostname()) if socket.gethostname() else "127.0.0.1",
        "ai_models": {
            "apple_vision": {
                "name": "Apple Vision (Neural Engine)",
                "status": "Ready" if platform.system() == "Darwin" and platform.machine() == "arm64" else "Unsupported",
                "version": "macOS Native",
                "active": platform.system() == "Darwin"
            },
            "paddle_ocr": {
                "name": "PaddleOCR-VL",
                "status": "Missing",
                "version": "N/A",
                "active": False
            },
            "mlx_vlm": {
                "name": "MLX-VLM Server",
                "status": "Missing",
                "version": "N/A",
                "active": False
            }
        }
    }
    
    try:
        import paddle
        info["ai_models"]["paddle_ocr"]["status"] = "Ready"
        info["ai_models"]["paddle_ocr"]["version"] = paddle.__version__
        info["ai_models"]["paddle_ocr"]["active"] = True
    except ImportError:
        pass
        
    try:
        import mlx.core as mx
        info["ai_models"]["mlx_vlm"]["status"] = "Ready"
        info["ai_models"]["mlx_vlm"]["version"] = mx.__version__
        info["ai_models"]["mlx_vlm"]["active"] = True
    except ImportError:
        pass
        
    return info
