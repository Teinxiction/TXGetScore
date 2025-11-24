import os
import sys
import subprocess
import platform
from pathlib import Path

class VGMStreamConverter:
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.is_linux = self.system == "linux"
        
        # 设置工具路径
        if self.is_windows:
            self.tool_dir = Path("vgmstream-win")
            self.cli_tool = self.tool_dir / "vgmstream-cli.exe"
        else:
            self.tool_dir = Path("vgmstream-linux-cli")
            self.cli_tool = self.tool_dir / "vgmstream-cli"
    
    def check_tool_available(self):
        """检查vgmstream工具是否可用"""
        if not self.tool_dir.exists():
            print(f"✗ 工具目录不存在: {self.tool_dir}")
            return False
        
        if not self.cli_tool.exists():
            print(f"✗ 找不到可执行文件: {self.cli_tool}")
            return False
        
        # Linux下确保有执行权限
        if self.is_linux:
            try:
                os.chmod(self.cli_tool, 0o755)
            except:
                pass
        
        print(f"✓ 找到vgmstream工具: {self.cli_tool}")
        return True
    
    def get_file_info(self, fsb_file):
        """获取FSB文件信息"""
        try:
            cmd = [str(self.cli_tool), "-i", str(fsb_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines[:10]:  # 只显示前10行信息
                    if line.strip():
                        print(f"    {line}")
            return True
        except Exception as e:
            print(f"    ✗ 获取文件信息失败: {e}")
            return False
    
    def convert_single_file(self, input_file, output_dir, output_format="wav"):
        """转换单个文件"""
        try:
            # 确保输出目录存在
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成输出文件名
            output_file = output_dir / f"{input_file.stem}.{output_format}"
            
            # 构建命令
            cmd = [str(self.cli_tool), "-o", str(output_file), str(input_file)]
            
            print(f"  执行: {' '.join(cmd)}")
            
            # 运行转换命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 检查输出文件是否真的生成了
                if output_file.exists() and output_file.stat().st_size > 0:
                    print(f"  ✓ 转换成功: {output_file.name}")
                    return True
                else:
                    print(f"  ✗ 输出文件未生成或为空")
                    return False
            else:
                print(f"  ✗ 转换失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"  ✗ 转换错误: {e}")
            return False
    
    def batch_convert(self, input_dir="music", output_dir="music-wav", output_format="wav"):
        """批量转换FSB文件"""
        print("=== vgmstream FSB批量转换工具 ===")
        print(f"系统: {platform.system()}")
        print(f"平台: {'Windows' if self.is_windows else 'Linux'}")
        print(f"工具路径: {self.cli_tool}")
        
        # 检查工具是否可用
        if not self.check_tool_available():
            print("vgmstream工具不可用，请检查:")
            print(f"  - 确保 {self.tool_dir} 目录存在")
            print(f"  - 确保 {self.cli_tool} 文件存在")
            return
        
        # 检查输入目录
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"✗ 输入目录不存在: {input_path}")
            print("请创建 'music' 文件夹并放入FSB文件")
            return
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 查找FSB文件
        fsb_files = list(input_path.glob("**/*.fsb"))
        if not fsb_files:
            print("✗ 未找到FSB文件")
            return
        
        print(f"找到 {len(fsb_files)} 个FSB文件")
        print("开始转换...\n")
        
        # 批量转换
        success_count = 0
        for i, fsb_file in enumerate(fsb_files, 1):
            print(f"[{i}/{len(fsb_files)}] 处理: {fsb_file.name}")
            
            # 显示文件信息（可选）
            # print("  文件信息:")
            # self.get_file_info(fsb_file)
            
            # 保持目录结构
            relative_path = fsb_file.relative_to(input_path)
            output_subdir = output_path / relative_path.parent
            output_subdir.mkdir(parents=True, exist_ok=True)
            
            if self.convert_single_file(fsb_file, output_subdir, output_format):
                success_count += 1
        
        # 输出结果
        print(f"\n🎉 转换完成!")
        print(f"成功: {success_count}/{len(fsb_files)} 个文件")
        print(f"输出目录: {output_path}")

def manual_convert_instructions():
    """手动转换说明"""
    print("\n=== 手动转换说明 ===")
    
    if platform.system().lower() == "windows":
        print("Windows手动转换:")
        print('  vgmstream-win\\vgmstream-cli.exe -o "输出文件.wav" "输入文件.fsb"')
        print("\n批量转换示例:")
        print('  for %i in (music\\*.fsb) do vgmstream-win\\vgmstream-cli.exe -o "music-wav\\%~ni.wav" "%i"')
    else:
        print("Linux手动转换:")
        print('  vgmstream-linux-cli/vgmstream-cli -o "输出文件.wav" "输入文件.fsb"')
        print("\n批量转换示例:")
        print('  for file in music/*.fsb; do')
        print('    vgmstream-linux-cli/vgmstream-cli -o "music-wav/$(basename "$file" .fsb).wav" "$file"')
        print('  done')

def main():
    """主函数"""
    converter = VGMStreamConverter()
    
    print("vgmstream FSB转换工具")
    print("=" * 40)
    
    # 直接运行批量转换
    try:
        converter.batch_convert()
    except Exception as e:
        print(f"程序运行出错: {e}")
        manual_convert_instructions()

main()