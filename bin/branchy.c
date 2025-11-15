#include <stdio.h>
int main(){
  volatile int sum=0;
  for (int i=0;i<2000000;i++){
    // predictable pattern: mostly true when i%8 != 0
    if ((i & 7) != 0) sum+=i; else sum-=i;
  }
  printf("sum=%d\n", sum);
  return 0;
}
