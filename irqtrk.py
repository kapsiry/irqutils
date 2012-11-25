#!/usr/bin/python
import re
import sys
from time import sleep
import sys
import argparse

line_format = '[%12s | %03s] %s [%10i | %5i]'
head_format = '[%12s | %03s] %s [%10s | %5s]'

match = 'IR-'
interval=1

def main():

    sys.stderr.write("\x1b[2J\x1b[H")

    iv_start = get_irq()
    old_irq = iv_start.copy()

    print_header()
    while True:
        curr_irq = get_irq()
        # set cursor to home
        sys.stderr.write("\x1b[H")
        # step one row down
        sys.stderr.write("\x1b[1B")
        print_irqdiff(curr_irq, old_irq, iv_start, interval)
        old_irq = curr_irq
        sleep(interval)

def print_header():
    print(head_format % ('name', 'IRQ', '+ = Current, # = Old, - = No', 'Interrupts', '1/sec'))

def print_irqdiff(curr_irq, old_irq, iv_start, interval):
    keys = curr_irq.keys()
    for k in sorted(keys):
        if old_irq[k] != None:
            print(get_diffline(k, curr_irq[k], old_irq[k], iv_start[k], interval))

def get_diffline(irq, curr_irqline, old_irqline, iv_start, interval):
    str = ""

    itot=0

    for i in range(0,len(curr_irqline)-2):
        ind = None

        diff_to_begin = int(curr_irqline[i])-int(iv_start[i])

        if curr_irqline[i] != old_irqline[i]:
            ind = '+'
        elif diff_to_begin != 0:
            ind = '#'
        else:
            ind = '-'
        str = str + " %s" % (ind) 

        itot += diff_to_begin

    stot=0

    for i in range(0,len(curr_irqline)-2):

        diff_to_old = int(curr_irqline[i])-int(old_irqline[i])
        stot += diff_to_old

    stot = stot / interval

    fstr = line_format % (curr_irqline[len(curr_irqline)-1], irq, str, itot, stot)

    return fstr

def get_irq():
    irqfile = open('/proc/interrupts', 'r')
    lines = irqfile.readlines()

    irqs = {}

    for line in lines:
        if len(line) > 2:
            irqline_res = parse_irqline(line, match)
            if irqline_res:
                irqs[irqline_res[0]] = irqline_res[1]

    return irqs

def parse_irqline(line, match):
    line = line.strip()

    if match not in line:
        return

    data = line.split(':')
    if len(data) != 2:
        return

    irq = data[0]
    irqdata = data[1]

    irq_per_core = []

    pattern = re.compile(r'\s+')
    irqdata_array = re.sub(pattern, ' ', irqdata.strip()).split(' ')
    name = []
    for core_irqs in irqdata_array:
        try:
            int(core_irqs)
        except:
            if core_irqs != 'interrupts' and '-edge' not in core_irqs and '-fasteoi' not in core_irqs:
                name.append(core_irqs)
            continue
        irq_per_core.append(core_irqs)

    try:
        int(irq)
        irq_per_core.append(' '.join(name))
    except:
        irq_per_core.append('')
    if len(irq_per_core) < 3:
        return
    return [irq, irq_per_core]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Displays IRQ usage')
    parser.add_argument('--interval','-i', help="refresh interval", nargs=1, type=float, default=1)
    parser.add_argument('--match','-m', help="match IRQ name", nargs=1, type=str, default='IR-')
    args = parser.parse_args()
    if len(args.interval) == 1:
        interval = float(args.interval[0])
    if len(args.match) == 1:
        match = args.match[0]
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
