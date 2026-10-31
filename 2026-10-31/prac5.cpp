#include <iostream>

int main(){
    double grade;
    std::cout << "enter grade\n";
    std::cin >> grade;
    if (grade < 0 || grade > 100 )
    {
        std::cout << "invalid data\n";
        return 0;
    } 
    else if (grade >= 90)
    {
        std::cout << "Excellent\n";
    }
    else if (grade >= 60)
    {
        std::cout << "Pass";
    }
    else if (grade < 60)
    {
        std::cout << "Fail";
    }
    return 0;
}