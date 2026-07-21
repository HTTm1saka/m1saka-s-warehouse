#include <iostream>
#include <cmath>
#include <iomanip>
using namespace std;
int main (){
    while (true)
    {
    double p , a , b , c;
    cout << "Enter the 3 sides of the triangle to calculate the area" << endl;
    cin >> a >> b >> c;
     p = 0.5 * (a + b + c);
    cout << setprecision(1) << fixed << sqrt (p * (p - a) * (p - b) * (p - c)) << endl;
    }
    return 0;
}