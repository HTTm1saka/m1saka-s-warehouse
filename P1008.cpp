#include <iostream>
using namespace std;

int main() {
    // 第一个数最小为 123,最大为 329(3 倍后不超过 987)
    for (int a = 123; a <= 329; a++) {
        int b = a * 2, c = a * 3;
        // 取出三个数的 9 位数字
        int digits[9] = {
            a / 100, a / 10 % 10, a % 10,
            b / 100, b / 10 % 10, b % 10,
            c / 100, c / 10 % 10, c % 10
        };
        bool used[10] = {false}; // used[i] 表示数字 i 是否已出现
        bool ok = true;
        for (int i = 0; i < 9; i++) {
            if (digits[i] == 0 || used[digits[i]]) { // 数字 0 不允许,重复不允许
                ok = false;
                break;
            }
            used[digits[i]] = true;
        }
        if (ok) cout << a << ' ' << b << ' ' << c << endl;
    }
    return 0;
}
