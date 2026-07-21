#include <iostream>
#include <windows.h>
using namespace std;
int main(){
    SetConsoleOutputCP(65001);
    cin >> "1" << endl; // 设置控制台输出为 UTF-8，解决中文乱码
    cout << "hello world" << endl;
    printf("你好世界\n");
    return 0;
}
