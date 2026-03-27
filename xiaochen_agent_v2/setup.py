"""
智匠 AgentForge (AGENTFORGE_TERMINAL) 安装脚本
用于 PyInstaller 构建时将包安装到虚拟环境
"""
from setuptools import setup, find_packages

setup(
    name="agentforge",
    version="2.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0",
        "urllib3>=2.0.0",
        "colorama>=0.4.6",
        "keyboard>=0.13.5",
        "Pillow>=10.0.0",
    ],
    python_requires=">=3.9",
    author="AgentForge",
    description="A powerful AI terminal assistant with OCR and web search capabilities",
    entry_points={
        'console_scripts': [
            'agentforge-agent=agentforge.ui.cli:run_cli',
        ],
    },
)
