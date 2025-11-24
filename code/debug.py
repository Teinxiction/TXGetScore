import filecmp
import os

def compare_files():
    source = "GetScore/PhiCloudAction/info/difficulty.tsv"
    target = "info/difficulty.tsv"
    
    if os.path.exists(source) and os.path.exists(target):
        # 比较文件内容是否相同
        if filecmp.cmp(source, target):
            print("两个文件内容完全相同")
        else:
            print("两个文件内容不同")
        
        # 检查文件大小
        source_size = os.path.getsize(source)
        target_size = os.path.getsize(target)
        print(f"源文件大小: {source_size} 字节")
        print(f"目标文件大小: {target_size} 字节")
        
        # 检查修改时间
        source_mtime = os.path.getmtime(source)
        target_mtime = os.path.getmtime(target)
        print(f"源文件修改时间: {source_mtime}")
        print(f"目标文件修改时间: {target_mtime}")
    else:
        print("文件不存在")

compare_files()
input()