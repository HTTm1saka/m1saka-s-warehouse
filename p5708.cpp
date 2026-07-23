#include <iostream>
#include <iomanip>
using namespace std;
int main(){
    int s, v , x , y;
    cin >> s >> v;
    x = s / v;
    y = x % 60;
    x <= 24;
    if (x <= 60)
    {
        if (y < 10)
        {
            cout << 07 << ":0" << 60 - x;
        }
       else  cout << 07 << ":" << 60 - x;
    }
    else {
        if ( x / 60 < 10)
        {
            if (y < 10)
            {
               cout << fixed << setprecision(0) << "0" << x / 60 << "0" << y;
            }
            
           else cout << fixed << setprecision(0) << "0" << x / 60 << y;
        }
        
       else 
            if (y < 10)
            {
               cout << fixed << setprecision(0) << x / 60 << "0" << y;
            }
            
           else cout << fixed << setprecision(0) << x / 60 << y;
        }
            
    }
