import os
import shutil

def replace_file_safe():
    """安全地替换文件（包含错误处理）"""
    source_file = "info/difficulty.tsv"
    target_file = "PhiCloudAction/info/difficulty.tsv"
    
    # 检查源文件是否存在
    if not os.path.exists(source_file):
        print(f"错误：源文件 '{source_file}' 不存在")
        return False
    
    try:
        # 如果目标目录不存在，创建目录
        target_dir = os.path.dirname(target_file)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir)
            print(f"创建目录: {target_dir}")
        
        # 复制文件
        shutil.copy2(source_file, target_file)
        print(f"成功将 '{source_file}' 替换为 '{target_file}'")
        return True
        
    except Exception as e:
        print(f"文件替换失败: {e}")
        return False

# 使用示例
replace_file_safe()