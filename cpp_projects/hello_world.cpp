/**
 * @file hello_world.cpp
 * @brief 一个简单的C++示例程序，展示基本语法和功能
 * 
 * 这个程序演示了：
 * 1. 基本的输入输出
 * 2. 函数定义和调用
 * 3. 条件语句
 * 4. 循环语句
 * 5. 简单的数学运算
 */

#include <iostream>
#include <string>

using namespace std;

/**
 * @brief 打印欢迎信息
 * 
 * 这个函数打印一个简单的欢迎信息到控制台
 */
void printWelcomeMessage() {
    cout << "======================================" << endl;
    cout << "     欢迎使用C++示例程序" << endl;
    cout << "======================================" << endl;
}

/**
 * @brief 计算两个整数的和
 * 
 * @param a 第一个整数
 * @param b 第二个整数
 * @return int 两个整数的和
 */
int addNumbers(int a, int b) {
    return a + b;
}

/**
 * @brief 判断一个数是否为偶数
 * 
 * @param number 要检查的整数
 * @return true 如果是偶数
 * @return false 如果是奇数
 */
bool isEven(int number) {
    return number % 2 == 0;
}

/**
 * @brief 打印乘法表
 * 
 * @param n 乘法表的大小
 */
void printMultiplicationTable(int n) {
    cout << "\n" << n << "x" << n << "乘法表：" << endl;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            cout << i * j << "\t";
        }
        cout << endl;
    }
}

/**
 * @brief 主函数
 * 
 * @return int 程序退出码
 */
int main() {
    // 设置控制台编码为UTF-8（Windows系统）
    #ifdef _WIN32
        system("chcp 65001 > nul");
    #endif

    printWelcomeMessage();

    // 基本输入输出示例
    string name;
    cout << "\n请输入您的名字: ";
    getline(cin, name);
    cout << "你好, " << name << "!" << endl;

    // 数学运算示例
    int num1, num2;
    cout << "\n请输入两个整数（用空格分隔）: ";
    cin >> num1 >> num2;

    int sum = addNumbers(num1, num2);
    cout << num1 << " + " << num2 << " = " << sum << endl;

    // 条件语句示例
    cout << "\n数字奇偶性检查：" << endl;
    for (int i = num1; i <= num2; i++) {
        if (isEven(i)) {
            cout << i << " 是偶数" << endl;
        } else {
            cout << i << " 是奇数" << endl;
        }
    }

    // 循环示例 - 打印乘法表
    int tableSize;
    cout << "\n请输入乘法表的大小 (1-10): ";
    cin >> tableSize;

    if (tableSize >= 1 && tableSize <= 10) {
        printMultiplicationTable(tableSize);
    } else {
        cout << "输入无效，请输入1-10之间的数字" << endl;
    }

    // 数组示例
    cout << "\n数组示例：" << endl;
    int numbers[] = {1, 2, 3, 4, 5};
    int arraySize = sizeof(numbers) / sizeof(numbers[0]);

    cout << "数组元素: ";
    for (int i = 0; i < arraySize; i++) {
        cout << numbers[i] << " ";
    }
    cout << endl;

    // 计算数组元素的和
    int arraySum = 0;
    for (int i = 0; i < arraySize; i++) {
        arraySum += numbers[i];
    }
    cout << "数组元素总和: " << arraySum << endl;

    // 程序结束
    cout << "\n======================================" << endl;
    cout << "     程序执行完毕，感谢使用！" << endl;
    cout << "======================================" << endl;

    cout << "\n按Enter键退出...";
    cin.ignore(); // 清除之前的换行符
    cin.get();    // 等待用户按Enter键

    return 0;
}