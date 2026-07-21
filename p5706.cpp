#include <iostream>
#include <iomanip>
using namespace std;
int main(){
    double t;
    int n;
    cin >> t >> n;
    cout << setprecision(3) << fixed << t/n << endl;
    cout << n * 2 << endl;
    return 0;
}