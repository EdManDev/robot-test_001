Physical Pin    GPIO (BCM)    L298N Pin    Wire Color Suggestion
──────────────────────────────────────────────────────────────
Pin 16          GPIO 23   →   IN1         Red (Motor A Dir 1)
Pin 18          GPIO 24   →   IN2         Orange (Motor A Dir 2)  
Pin 22          GPIO 25   →   IN3         Yellow (Motor B Dir 1)
Pin 24          GPIO 8    →   IN4         Green (Motor B Dir 2)
Pin 12          GPIO 18   →   ENA         Blue (Motor A Enable)
Pin 32          GPIO 12   →   ENB         Purple (Motor B Enable)
Pin 2           5V        →   VCC         Red (Power)
Pin 6           GND       →   GND         Black (Ground)


.   3.3V  [1] [2]  5V      ← Pin 2 (5V to L298N VCC)
          [3] [4]  5V
          [5] [6]  GND     ← Pin 6 (GND to L298N GND)
          [7] [8]
     GND  [9] [10]
         [11] [12] GPIO18  ← Pin 12 (ENA - Motor A Enable)
         [13] [14] GND
         [15] [16] GPIO23  ← Pin 16 (IN1 - Motor A Dir 1)
         [17] [18] GPIO24  ← Pin 18 (IN2 - Motor A Dir 2)
         [19] [20] GND
         [21] [22] GPIO25  ← Pin 22 (IN3 - Motor B Dir 1)
   GPIO8 [23] [24] GPIO8   ← Pin 24 (IN4 - Motor B Dir 2)
         [25] [26]
         [27] [28]
         [29] [30] GND
         [31] [32] GPIO12  ← Pin 32 (ENB - Motor B Enable)



