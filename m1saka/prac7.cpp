#include <iostream>

int main()
{
    int num;
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
                std::cout << base << std::endl;
            }
            
        }
        return 0;
}   