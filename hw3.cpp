#include <iostream>
#include <string>
int main (){
    double age;
    std::cin >> age;
    if (age >= 18)
    {
        std::cout << "adult" << std::endl;
    }
    else{
        std::cout << "minor" << std::endl;
    }
    return 0;
}