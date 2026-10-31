#include <iostream>

int main(){
    int num;
    int a = 0;
    std::cin >> num;
    std::cout << std::endl;
    if (num <= 0)
    {
        std::cout << "invalid data";
        return 0;
    }
    else 
        {
            for (int base = 1; base <= num; base = base + 2)
            {
                a = base + a;
            }
            std::cout << a << std::endl;
            return 0;
        }
}