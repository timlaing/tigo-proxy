import csv
import io

data = b"DATETIME,TimeStamp,GMT,LMU_A1_RSSI,LMU_A1_PWM,LMU_A1_Vin,LMU_A1_Temp,LMU_A1_Pin,LMU_A1_Vout,LMU_A2_RSSI,LMU_A2_PWM,LMU_A2_Vin,LMU_A2_Temp,LMU_A2_Pin,LMU_A2_Vout,LMU_A3_RSSI,LMU_A3_PWM,LMU_A3_Vin,LMU_A3_Temp,LMU_A3_Pin,LMU_A3_Vout,LMU_A4_RSSI,LMU_A4_PWM,LMU_A4_Vin,LMU_A4_Temp,LMU_A4_Pin,LMU_A4_Vout,LMU_A5_RSSI,LMU_A5_PWM,LMU_A5_Vin,LMU_A5_Temp,LMU_A5_Pin,LMU_A5_Vout,LMU_A6_RSSI,LMU_A6_PWM,LMU_A6_Vin,LMU_A6_Temp,LMU_A6_Pin,LMU_A6_Vout,LMU_A7_RSSI,LMU_A7_PWM,LMU_A7_Vin,LMU_A7_Temp,LMU_A7_Pin,LMU_A7_Vout,LMU_A8_RSSI,LMU_A8_PWM,LMU_A8_Vin,LMU_A8_Temp,LMU_A8_Pin,LMU_A8_Vout,LMU_B1_RSSI,LMU_B1_PWM,LMU_B1_Vin,LMU_B1_Temp,LMU_B1_Pin,LMU_B1_Vout,LMU_B2_RSSI,LMU_B2_PWM,LMU_B2_Vin,LMU_B2_Temp,LMU_B2_Pin,LMU_B2_Vout,LMU_B3_RSSI,LMU_B3_PWM,LMU_B3_Vin,LMU_B3_Temp,LMU_B3_Pin,LMU_B3_Vout,LMU_B4_RSSI,LMU_B4_PWM,LMU_B4_Vin,LMU_B4_Temp,LMU_B4_Pin,LMU_B4_Vout,LMU_B5_RSSI,LMU_B5_PWM,LMU_B5_Vin,LMU_B5_Temp,LMU_B5_Pin,LMU_B5_Vout,LMU_B6_RSSI,LMU_B6_PWM,LMU_B6_Vin,LMU_B6_Temp,LMU_B6_Pin,LMU_B6_Vout,LMU_B7_RSSI,LMU_B7_PWM,LMU_B7_Vin,LMU_B7_Temp,LMU_B7_Pin,LMU_B7_Vout,LMU_C1_RSSI,LMU_C1_PWM,LMU_C1_Vin,LMU_C1_Temp,LMU_C1_Pin,LMU_C1_Vout,LMU_C2_RSSI,LMU_C2_PWM,LMU_C2_Vin,LMU_C2_Temp,LMU_C2_Pin,LMU_C2_Vout,LMU_C3_RSSI,LMU_C3_PWM,LMU_C3_Vin,LMU_C3_Temp,LMU_C3_Pin,LMU_C3_Vout,LMU_C4_RSSI,LMU_C4_PWM,LMU_C4_Vin,LMU_C4_Temp,LMU_C4_Pin,LMU_C4_Vout,LMU_C5_RSSI,LMU_C5_PWM,LMU_C5_Vin,LMU_C5_Temp,LMU_C5_Pin,LMU_C5_Vout,LMU_C6_RSSI,LMU_C6_PWM,LMU_C6_Vin,LMU_C6_Temp,LMU_C6_Pin,LMU_C6_Vout\n2024/04/20 19:48:00.000,1713638880.000000,3600,116,254,29,18,7,28,96,254,29,21,7,28,86,241,18,19,4,16,75,255,29,20,7,28,84,252,27,20,6,27,96,236,21,19,5,18,119,254,28,19,7,28,108,254,28,19,6,28,163,255,29,20,7,28,99,255,29,20,7,29,116,255,29,19,7,29,129,255,29,18,7,29,254,255,29,18,7,29,91,255,29,20,7,29,83,255,28,17,7,28,,,,,,,87,255,29,18,7,29,69,255,28,18,6,28,128,255,28,19,6,28,,,,,,,96,255,28,17,6,27\n2024/04/20 19:49:00.000,1713638940.000000,3600,116,255,29,18,7,28,96,255,29,21,7,28,84,240,19,19,4,17,75,255,29,20,7,28,84,255,27,20,6,27,95,236,22,19,5,19,122,255,28,19,6,28,108,255,28,19,6,27,163,255,29,20,6,28,99,255,29,20,7,28,116,255,29,19,6,29,128,255,29,18,6,29,254,255,29,18,6,28,90,255,29,20,6,29,81,255,26,17,6,26,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n2024/04/20 19:50:00.000,1713639000.000000,3600,116,255,29,19,6,29,96,255,29,20,6,29,85,248,24,19,5,23,75,255,29,20,6,29,86,253,24,20,5,23,96,238,17,19,3,15,122,255,29,19,6,28,108,255,28,19,6,28,163,255,28,20,6,28,99,255,28,20,6,28,116,255,29,18,6,28,129,255,29,18,6,29,254,255,28,18,6,28,90,255,28,20,6,28,81,255,26,17,6,26,87,255,29,18,6,29,,,,,,,,,,,,,,,,,,,96,255,28,17,6,28,96,255,24,18,5,24\n2024/04/20 19:51:00.000,1713639060.000000,3600,117,255,29,18,6,29,96,255,29,20,6,29,84,255,29,19,6,29,75,255,29,20,6,29,84,241,19,19,3,17,96,236,18,19,3,16,121,255,29,19,6,29,108,255,29,19,6,29,163,255,28,20,6,27,99,255,28,20,6,28,116,255,29,18,6,28,128,255,29,18,6,28,253,255,28,18,6,28,91,255,28,20,6,28,82,255,25,17,5,25,87,255,29,20,5,29,87,255,29,18,6,28,69,255,29,17,5,28,128,255,29,18,6,28,96,255,29,16,6,29,96,255,27,18,5,26\n2024/04/20 19:52:00.000,1713639120.000000,3600,116,255,29,18,6,28,95,255,29,20,6,28,85,255,28,19,6,28,75,255,29,20,6,28,84,236,19,19,3,17,99,232,20,19,4,17,121,255,28,19,6,28,108,255,28,18,5,28,163,255,28,20,6,28,99,255,28,20,6,28,116,255,29,18,6,28,128,255,29,18,6,29,254,255,28,18,5,28,93,255,28,19,6,28,82,255,27,17,5,27,87,255,29,20,5,29,87,255,28,18,5,28,70,255,28,16,5,28,128,255,28,18,5,28,,,,,,,96,255,26,18,5,26\n2024/04/20 19:53:00.000,1713639180.000000,3600,116,255,29,19,6,29,98,255,29,20,6,29,85,255,29,19,5,28,75,255,29,20,5,29,84,238,19,19,3,16,95,235,22,18,4,19,119,255,29,19,5,28,108,255,28,18,5,28,163,255,28,20,5,27,99,255,28,20,5,28,116,255,29,18,5,28,128,255,29,18,5,28,254,255,28,18,5,28,92,255,28,20,5,28,81,255,27,17,5,26,87,255,29,20,5,29,87,255,29,18,5,28,69,255,28,17,5,28,128,255,28,18,5,28,95,255,29,16,5,29,96,216,19,18,3,15\n2024/04/20 19:54:00.000,1713639240.000000,3600,116,255,29,18,5,29,97,255,29,20,5,29,84,255,29,20,5,28,74,255,29,20,5,29,84,234,19,19,3,17,94,234,17,18,3,15,120,255,29,19,5,28,108,255,28,18,5,28,162,255,28,20,5,28,99,255,28,20,5,28,116,255,29,18,5,28,128,255,29,18,5,28,254,255,28,18,5,28,90,255,28,19,5,28,82,255,27,17,5,27,88,255,29,19,5,29,87,232,21,18,3,18,,,,,,,128,255,29,18,5,29,94,255,29,16,5,29,96,225,20,17,3,16\n2024/04/20 19:55:00.000,1713639300.000000,3600,116,255,29,18,5,29,96,255,29,20,5,29,84,255,28,19,5,28,75,255,29,20,5,29,82,231,19,19,3,16,97,231,22,18,3,19,119,255,29,19,5,28,108,255,28,17,5,28,163,255,28,19,5,27,99,255,28,20,5,28,116,255,28,18,5,28,129,255,29,18,5,28,254,255,28,17,5,28,92,255,28,19,5,28,83,255,25,16,4,24,87,255,29,19,5,29,,,,,,,,,,,,,,,,,,,93,255,29,16,5,29,96,232,26,17,4,24\n2024/04/20 19:56:00.000,1713639360.000000,3600,116,255,29,18,5,29,96,255,29,20,5,29,84,255,29,19,5,29,75,255,29,20,5,29,84,237,19,18,3,17,94,231,19,18,3,16,119,255,29,19,5,29,107,255,29,18,4,29,163,255,27,19,5,27,99,255,28,20,5,27,116,255,28,18,5,28,129,255,28,17,5,28,254,255,28,18,5,27,92,255,28,19,5,28,82,255,25,17,4,25,87,255,30,19,4,30,87,255,29,19,4,29,,,,,,,,,,,,,,,,,,,,,,,,\n2024/04/20 19:57:00.000,1713639420.000000,3600,117,255,29,18,5,29,97,255,29,19,5,29,84,255,29,19,4,29,74,255,29,20,4,29,83,238,19,19,2,17,96,237,19,18,3,16,119,255,29,18,4,29,107,255,29,18,4,29,163,255,27,20,4,27,99,255,28,20,5,27,116,255,28,18,4,28,128,255,28,17,4,28,254,255,28,17,4,27,91,255,28,19,4,28,83,255,25,17,4,25,87,255,30,19,4,29,87,255,29,19,4,29,78,255,30,17,4,29,,,,,,,69,255,30,16,4,30,,,,,,\n"
str_data = data.decode("utf-8")

print(csv.list_dialects())
reader = csv.DictReader(
    io.StringIO(str_data),
    dialect="unix",
)
for row in reader:
    print(row)
    break
