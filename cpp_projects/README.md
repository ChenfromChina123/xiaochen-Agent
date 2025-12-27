# C++ 示例项目

这是一个简单的C++示例项目，展示了基本的C++编程概念和语法。

## 项目结构

```
cpp_projects/
├── hello_world.cpp    # 主程序源代码
├── CMakeLists.txt     # CMake构建配置文件
└── README.md          # 项目说明文档
```

## 程序功能

这个示例程序演示了以下C++特性：

1. **基本输入输出** - 使用`cin`和`cout`进行用户交互
2. **函数定义和调用** - 定义和调用自定义函数
3. **条件语句** - 使用`if-else`进行条件判断
4. **循环语句** - 使用`for`循环
5. **数组操作** - 数组的声明、初始化和遍历
6. **数学运算** - 基本的算术运算

## 编译和运行

### 方法一：使用CMake（推荐）

1. 创建构建目录：
   ```bash
   mkdir build
   cd build
   ```

2. 运行CMake生成构建文件：
   ```bash
   cmake ..
   ```

3. 编译程序：
   ```bash
   cmake --build .
   ```

4. 运行程序：
   ```bash
   # Windows
   .\bin\hello_world.exe

   # Linux/Mac
   ./bin/hello_world
   ```

### 方法二：直接使用编译器

#### Windows (MinGW/GCC)
```bash
g++ -o hello_world.exe hello_world.cpp -std=c++11
.\hello_world.exe
```

#### Windows (MSVC)
```bash
cl /EHsc hello_world.cpp
hello_world.exe
```

#### Linux/Mac
```bash
g++ -o hello_world hello_world.cpp -std=c++11
./hello_world
```

## 程序使用说明

1. 程序启动后会显示欢迎信息
2. 输入您的名字
3. 输入两个整数，程序会计算它们的和
4. 程序会检查这两个整数之间所有数字的奇偶性
5. 输入一个数字（1-10）来生成乘法表
6. 程序会展示数组操作的示例
7. 按Enter键退出程序

## 代码说明

### 主要函数

- `printWelcomeMessage()`: 打印欢迎信息
- `addNumbers(int a, int b)`: 计算两个整数的和
- `isEven(int number)`: 判断一个数是否为偶数
- `printMultiplicationTable(int n)`: 打印n×n乘法表
- `main()`: 程序主函数，协调所有功能

### 编码设置

程序在Windows系统上会自动设置控制台编码为UTF-8，确保中文字符正确显示。

## 学习要点

通过这个示例程序，您可以学习到：

1. C++程序的基本结构
2. 如何组织代码到不同的函数中
3. 基本的控制流语句
4. 数组和循环的使用
5. 用户输入和输出的处理

## 扩展建议

您可以尝试修改这个程序来：

1. 添加更多的数学运算函数（减法、乘法、除法）
2. 实现更复杂的数据结构
3. 添加文件读写功能
4. 创建图形界面版本
5. 添加错误处理机制

## 系统要求

- C++编译器（GCC 4.8+、Clang 3.3+、MSVC 2015+）
- CMake 3.10+（可选，用于构建）
- Windows/Linux/Mac操作系统

## 许可证

本项目仅供学习使用，遵循MIT许可证。