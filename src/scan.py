import machine

# Create I2C object
i2c = machine.I2C(0, scl=machine.Pin(9), sda=machine.Pin(8))
print("have I2c")
# Print out any addresses found
devices = i2c.scan()

if devices:
    for d in devices:
        print(hex(d))