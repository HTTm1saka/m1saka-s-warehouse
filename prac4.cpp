#include <iostream>

int main(){
    double price;
    double quantity;
    std::cout << "Enter price, quantity." << std::endl;
    std::cin >> price >> quantity;
    double total = price * quantity;
    if (total >= 100)
    {
       double pay = total - 10;
       std::cout << "Total:" << total << "\n" << "Discount:10\n" << "Pay:" << pay << std::endl;
    }
    else
    {
        std::cout << total << "\n" << "No discount\n" << "Pay:" << total << std::endl;
    }
    return 0;
}