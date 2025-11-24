import os
import requests
import re
import subprocess
import sys
from pathlib import Path

def ensure_directory(directory):
    """确保目录存在"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = size_bytes
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    return f"{size:.1f}{units[unit_index]}"

def download_file(url, filepath):
    """下载文件并显示进度"""
    print(f"正在下载: {url}")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 显示下载进度
                    if total_size > 0:
                        percent = (downloaded_size / total_size) * 100
                        progress_bar = f"[{percent:.1f}%]"
                        size_info = f"{format_size(downloaded_size)}/{format_size(total_size)}"
                        print(f"\r{progress_bar} {size_info}", end='', flush=True)
                    else:
                        print(f"\r[{format_size(downloaded_size)}]", end='', flush=True)
        
        print("\n下载完成!")
        return True
        
    except Exception as e:
        print(f"\n下载失败: {e}")
        return False

def is_valid_apk(filepath):
    """检查文件是否是有效的APK文件"""
    try:
        if not os.path.exists(filepath):
            return False
        
        file_size = os.path.getsize(filepath)
        if file_size < 1024 * 1024:
            return False
        
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header != b'PK\x03\x04':
                return False
        
        return True
        
    except Exception:
        return False

def is_html_file(filepath):
    """检查文件是否是HTML文件"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read(1024)
            content_str = content.decode('utf-8', errors='ignore')
            
            html_indicators = ['<html', '<!DOCTYPE', '<title>', '<head>', '<body>']
            for indicator in html_indicators:
                if indicator.lower() in content_str.lower():
                    return True
            
            return False
            
    except Exception:
        return False

def run_taptap_script():
    """运行taptap.py脚本获取新的下载链接"""
    print("运行taptap.py获取新的下载链接...")
    try:
        result = subprocess.run([sys.executable, 'taptap.py'], 
                              capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False

def read_download_url():
    """从download.txt读取下载链接"""
    download_file = "download.txt"
    if not os.path.exists(download_file):
        return None
    
    try:
        with open(download_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        urls = re.findall(url_pattern, content)
        
        if urls:
            url = urls[0]
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        else:
            return None
            
    except Exception:
        return None

def run_resource_script(apk_path):
    print(f"请滚去运行resource.py处理APK文件: {apk_path}（python resource.py {apk_path}）")

def main():
    """主函数"""
    # 检查是否手动指定了APK路径
    if len(sys.argv) > 1:
        manual_apk_path = sys.argv[1]
        if os.path.exists(manual_apk_path):
            run_resource_script(manual_apk_path)
            return
    
    # 确保目录存在
    ensure_directory("PhigrosApk")
    apk_path = "PhigrosApk/base.apk"
    
    download_attempts = 0
    max_attempts = 3
    download_success = False
    
    while download_attempts < max_attempts and not download_success:
        download_attempts += 1
        print(f"\n=== 下载尝试 #{download_attempts} ===")
        
        # 读取下载链接，如果没有则运行taptap.py
        download_url = read_download_url()
        if not download_url:
            print("没有找到下载链接，运行taptap.py...")
            run_taptap_script()
            download_url = read_download_url()
            if not download_url:
                print("taptap.py执行后仍未找到下载链接")
                continue
        
        # 下载文件
        temp_path = "PhigrosApk/temp_download"
        if download_file(download_url, temp_path):
            
            if is_valid_apk(temp_path):
                print("下载的文件是有效的APK")
                # 直接覆盖原有的base.apk
                if os.path.exists(apk_path):
                    os.remove(apk_path)
                os.rename(temp_path, apk_path)
                print(f"APK文件已保存为: {apk_path}")
                download_success = True
                
            elif is_html_file(temp_path):
                print("下载的文件是HTML页面（链接已过期）")
                os.remove(temp_path)
                print("运行taptap.py获取新链接...")
                run_taptap_script()
            else:
                print("下载的文件不是有效的APK")
                os.remove(temp_path)
                print("运行taptap.py获取新链接...")
                run_taptap_script()
        else:
            print("下载失败，运行taptap.py获取新链接...")
            run_taptap_script()
    
    # 确保运行resource.py
    if download_success and os.path.exists(apk_path) and is_valid_apk(apk_path):
        print("\n=== 开始处理APK资源 ===")
        if not run_resource_script(apk_path):
            print("资源处理失败")
    else:
        print("无法获取有效的APK文件")


main()