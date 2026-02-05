#!/usr/bin/env python3
"""
DeskJarvis Planner 测试脚本

用于测试升级后的 System Prompt 功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent.tools.config import Config
from agent.tools.logger import setup_logger
from agent.planner.claude_planner import ClaudePlanner

setup_logger()

def test_planner(instruction: str):
    """测试 Planner 规划功能"""
    print("=" * 60)
    print(f"📝 测试指令: {instruction}")
    print("=" * 60)
    
    try:
        config = Config()
        planner = ClaudePlanner(config)
        
        # 规划任务
        steps = planner.plan(instruction)
        
        print(f"\n✅ 规划成功，生成 {len(steps)} 个步骤\n")
        
        # 显示每个步骤
        for i, step in enumerate(steps, 1):
            print(f"步骤 {i}:")
            print(f"  类型: {step.get('type')}")
            print(f"  操作: {step.get('action')}")
            print(f"  描述: {step.get('description')}")
            
            # 如果是脚本，显示详细信息
            if step.get('type') == 'execute_python_script':
                params = step.get('params', {})
                print(f"  原因: {params.get('reason', 'N/A')}")
                print(f"  安全: {params.get('safety', 'N/A')}")
                script = params.get('script', '')
                if script:
                    # 显示脚本的前几行
                    lines = script.split('\\n')[:5]
                    print(f"  脚本预览:")
                    for line in lines:
                        print(f"    {line}")
                    if len(script.split('\\n')) > 5:
                        print(f"    ... (共 {len(script.split('\\n'))} 行)")
            
            print()
        
        return steps
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 测试用例列表
    test_cases = [
        # 简单任务 - 应该使用工具
        {
            "name": "测试用例 1: 简单文件创建",
            "instruction": "在桌面创建一个名为 test.txt 的文件，内容为 'Hello, DeskJarvis!'",
            "expected_tool": "file_create",
            "should_use_script": False
        },
        {
            "name": "测试用例 2: 文件重命名",
            "instruction": "将桌面上的 test.txt 重命名为 hello.txt",
            "expected_tool": "file_rename",
            "should_use_script": False
        },
        # 复杂任务 - 应该使用脚本
        {
            "name": "测试用例 3: 批量文件处理",
            "instruction": "在沙盒目录中创建 10 个测试文件（test1.txt 到 test10.txt），每个文件内容为对应的数字（1 到 10），然后统计这些文件的总数和总字符数，将结果保存到 report.txt",
            "expected_tool": None,
            "should_use_script": True
        },
        {
            "name": "测试用例 4: 数据分析",
            "instruction": "在沙盒目录中创建一个包含 100 个随机数字（1-100）的文件 numbers.txt，每行一个数字，然后计算平均值、最大值、最小值，并将统计结果保存到 stats.txt",
            "expected_tool": None,
            "should_use_script": True
        }
    ]
    
    print("🚀 DeskJarvis Planner 测试开始\n")
    
    # 运行所有测试用例
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'='*60}\n")
        
        steps = test_planner(test_case['instruction'])
        
        if steps:
            # 验证结果
            step_types = [step.get('type') for step in steps]
            has_script = 'execute_python_script' in step_types
            
            print("📊 验证结果:")
            if test_case['should_use_script']:
                if has_script:
                    print("  ✅ 正确：使用了脚本生成")
                else:
                    print("  ⚠️  警告：应该使用脚本，但使用了工具")
            else:
                if has_script:
                    print("  ⚠️  警告：不应该使用脚本，但使用了脚本")
                else:
                    print("  ✅ 正确：使用了预定义工具")
            
            if test_case['expected_tool']:
                if test_case['expected_tool'] in step_types:
                    print(f"  ✅ 正确：使用了 {test_case['expected_tool']} 工具")
                else:
                    print(f"  ⚠️  警告：应该使用 {test_case['expected_tool']}，但使用了 {step_types}")
        
        print("\n" + "-" * 60 + "\n")
    
    print("🎉 所有测试完成！")
