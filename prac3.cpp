#include <iostream>
using namespace std;
int main(){
    int price;
    int quantity;
    cout << "Enter price, quantity." << endl;
    cin >> price >> quantity;
    int total = price * quantity;
    cout << "Total:" << total << endl;
    return 0;
}