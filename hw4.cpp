#include <string>
#include <iostream>
int main(){
    int number;
    std::cin >> number;
    bool tf = (number > 0 && number % 2 == 0);
     std::cout << std::boolalpha << tf << std::endl;
     return 0;
}
