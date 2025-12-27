# CMake最低版本要求
cmake_minimum_required(VERSION 3.10)

# 项目名称和版本
project(HelloWorld VERSION 1.0.0 LANGUAGES CXX)

# 设置C++标准
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 设置输出目录
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# 添加可执行文件
add_executable(hello_world hello_world.cpp)

# 设置目标属性
set_target_properties(hello_world PROPERTIES
    OUTPUT_NAME "hello_world"
    VERSION ${PROJECT_VERSION}
)

# 在Windows上设置UTF-8编码
if(WIN32)
    target_compile_definitions(hello_world PRIVATE _WIN32)
endif()

# 安装规则
install(TARGETS hello_world
    RUNTIME DESTINATION bin
)

# 可选：添加测试
enable_testing()

# 添加一个简单的测试
add_test(NAME RunHelloWorld
    COMMAND hello_world
)