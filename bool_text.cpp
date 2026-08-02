#include <iostream>
int main (){
    int n;
    std::cin >> n;
    bool a = (n >= 0);  // 把判断结果（true/false）存入 bool 变量
    if (a)
    {
        std::cout << "right" << std::endl;
    }
    else
    {
        std::cout << "wrong" << std::endl;
    }
    return 0;
}