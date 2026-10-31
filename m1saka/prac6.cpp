#include <iostream>

int main(){
    std::cout << "enter a number\n";
    int num;
    std::cin >> num;
    if (num % 2 == 0)
    {
        std::cout << "even\n";
    }
    else
    {
        std::cout << "odd\n";
    }
    return 0;
}