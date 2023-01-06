package main

import (
	"fmt"
	"image/color"
	"machine"
	"strings"
	"time"
	"tinygo.org/x/drivers/st7789"
	"tinygo.org/x/tinyfont"
	"tinygo.org/x/tinyfont/freemono"
	"tinygo.org/x/tinyfont/proggy"
)

var colorMap = map[string]color.RGBA{
	"blue":  color.RGBA{0, 0, 255, 255},
	"white": color.RGBA{255, 255, 255, 255},
	"green": color.RGBA{0, 255, 0, 255},
	"red":   color.RGBA{255, 0, 0, 255},
	"black": color.RGBA{0, 0, 0, 255},
	"orange": color.RGBA{230, 126, 34, 255},
	"pink": color.RGBA{190, 86, 131, 255},
	"purple": color.RGBA{165, 55, 253, 255},
	"yellow": color.RGBA{255, 240, 0, 255},
	"brown": color.RGBA{139, 69, 19, 255},
}

func main() {
	machine.SPI0.Configure(machine.SPIConfig{
		Frequency: 8000000,
		Mode:      3,
		SDO:       machine.GP3,
		SCK:       machine.GP2,
	})
	display := st7789.New(machine.SPI0,
		machine.GP0,
		machine.GP1,
		machine.GP5,
		machine.GP4)
	//NO_ROTATION: use rowoffset=40,coloffset=53 width=135, height=240
	//ROTATION_90: use rowoffset=40,coloffset=52 width=135, height=240
	display.Configure(st7789.Config{
		Width:        135,
		Height:       240,
		Rotation:     st7789.ROTATION_90,
		RowOffset:    40,
		ColumnOffset: 52,
	})

	display.FillScreen(colorMap["black"])

	uart := machine.UART1
	uart.Configure(machine.UARTConfig{
		BaudRate: 38400,
		TX:       machine.GP8,
		RX:       machine.GP9,
	})

	input := make([]byte, 64)
	i := 0
	j := 15

	for {
		if uart.Buffered() > 0 {
			data, _ := uart.ReadByte()

			switch data {
			case 38: //? = &
				j = 10
				display.FillScreen(colorMap["black"])
			case 35: //End of line received: 35 = #
				display.FillScreen(colorMap["black"])
				tiltData := strings.Split(string(input[:i]), ",")
				if len(tiltData) > 1 {
					tinyfont.WriteLine(&display, &freemono.Regular12pt7b, 20, int16(15), fmt.Sprintf("Tilt | %s", strings.ToUpper(tiltData[0])), colorMap[tiltData[0]])
					tinyfont.WriteLine(&display, &freemono.Regular12pt7b, 10, int16(55), fmt.Sprintf("Gravity:  %s", tiltData[2]), colorMap[tiltData[0]])
					tinyfont.WriteLine(&display, &freemono.Regular12pt7b, 10, int16(80), fmt.Sprintf("Temp:     %s°F", tiltData[1]), colorMap[tiltData[0]])
				} else {
					if j > 115 {
						j = 10
						display.FillScreen(colorMap["black"])
					}
					tinyfont.WriteLine(&display, &proggy.TinySZ8pt7b, 10, int16(+40), string(input[:i]), colorMap["brown"])
					j += 10
		      time.Sleep(1000)
				}
				i = 0
			default:
				input[i] = data
				i++
			}
		}
		time.Sleep(5 * time.Millisecond)
	}

}
