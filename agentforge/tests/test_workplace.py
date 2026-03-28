"""
测试Agent专属工作目录(WorkPlace)功能
"""
import os
import sys
import tempfile
import shutil

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# 只导入文件工具模块进行测试
import importlib.util
spec = importlib.util.spec_from_file_location("files", os.path.join(project_root, "utils", "files.py"))
files_module = importlib.util.module_from_spec(spec)
sys.modules["files"] = files_module
spec.loader.exec_module(files_module)

get_workplace_root = files_module.get_workplace_root


def test_get_workplace_root():
    """测试获取工作目录根路径"""
    workplace = get_workplace_root()
    print(f"WorkPlace路径: {workplace}")
    assert os.path.exists(workplace), "工作目录应该存在"
    assert os.path.isdir(workplace), "工作目录应该是目录"
    print("✓ get_workplace_root() 测试通过")


def test_workplace_env_override():
    """测试环境变量覆盖工作目录路径"""
    original_env = os.environ.get("AGENTFORGE_WORKPLACE_DIR")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["AGENTFORGE_WORKPLACE_DIR"] = tmpdir
            # 重新加载模块以刷新
            spec2 = importlib.util.spec_from_file_location("files2", os.path.join(project_root, "utils", "files.py"))
            files_module2 = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(files_module2)
            
            workplace = files_module2.get_workplace_root()
            assert workplace == tmpdir, f"环境变量应该覆盖默认路径: {workplace} != {tmpdir}"
            print(f"环境变量覆盖后的路径: {workplace}")
            print("✓ 环境变量覆盖测试通过")
    finally:
        # 恢复原始环境变量
        if original_env is None:
            os.environ.pop("AGENTFORGE_WORKPLACE_DIR", None)
        else:
            os.environ["AGENTFORGE_WORKPLACE_DIR"] = original_env


def test_workplace_structure():
    """测试工作目录结构"""
    workplace = get_workplace_root()
    
    # 测试可以创建子目录
    test_subdir = os.path.join(workplace, "test_subdir")
    os.makedirs(test_subdir, exist_ok=True)
    assert os.path.exists(test_subdir), "应该能创建子目录"
    
    # 测试可以创建文件
    test_file = os.path.join(test_subdir, "test_file.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("测试内容")
    assert os.path.exists(test_file), "应该能创建文件"
    
    # 清理
    if os.path.exists(test_subdir):
        shutil.rmtree(test_subdir)
    
    print("✓ 工作目录结构测试通过")


if __name__ == "__main__":
    print("=" * 50)
    print("测试Agent专属工作目录(WorkPlace)功能")
    print("=" * 50)
    
    test_get_workplace_root()
    print()
    test_workplace_structure()
    print()
    test_workplace_env_override()
    
    print()
    print("=" * 50)
    print("所有测试通过!")
    print("=" * 50)
