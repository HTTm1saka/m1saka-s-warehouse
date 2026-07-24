#include <iostream>
#include <iomanip>
using namespace std;
int main(){
    double weight, height, bmi;
    cout << "Enter your height(cm) and weight(kg) to calculate your BMI" << endl;
    cin >> height >> weight;
    bmi = weight / (height * height) * 10000;
    cout << fixed << setprecision(1) << bmi << "  ";
    if (bmi < 18.5)
        cout << "too thin";
    else if (bmi < 25)
        cout << "common";
    else if (bmi < 30)
        cout << "too heavy";
    else
        cout << "you are a boomer";
    cout << endl;
    cout << "Press Enter to exit...";
    cin.ignore(1000, '\n');
    cin.get();
    return 0;
}