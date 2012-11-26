#!/usr/bin/python
import re
import sys
from time import sleep
import sys
import argparse
import curses

line_format = '[%12s | %03s] %s [%10i | %5i]'
head_format = '[%12s | %03s] %s [%10s | %5s]'

# Nearly every interesting interrupt have dash on its name
match = '-'
interval=1

scr = None
pad = None
scroll = 0

def main():
    global scroll,scr,pad
    y,x = scr.getmaxyx()
    irq_count = len(get_irq())
    pad = curses.newpad(irq_count, x)
    curses.noecho()
    # instant key input
    curses.cbreak()

    iv_start = get_irq()
    old_irq = iv_start.copy()

    scr.timeout(int(interval * 50))
    print_header()
    while True:
        curr_irq = get_irq()
        print_irqdiff(curr_irq, old_irq, iv_start, interval)
        old_irq = curr_irq
        pad.refresh(scroll, 0, 1, 0, y-1, x-1)
        g = 0
        while True:
            c = scr.getch()
            if c == curses.KEY_UP:
                if scroll > 0:
                    scroll -= 1
                break
            elif c == curses.KEY_DOWN:
                if scroll <= (irq_count - y):
                    scroll += 1
                break
            g += 1
            if g > 19:
                break
            #sleep(interval / 20.0)

def print_header():
    cpus = get_cpu_count()
    center = '+ = Current, # = Old, - = No'
    for i in range((cpus * 2 - 2) - len(center)):
        if (i % 2) == 0:
            center += ' '
        else:
            center = ' ' + center
    scr.addstr(0, 0, head_format % ('name', 'IRQ', center,
                  'Interrupts', '1/sec'))

def print_irqdiff(curr_irq, old_irq, iv_start, interval):
    global scroll
    row = 0
    keys = curr_irq.keys()
    for k in sorted(keys):
        if old_irq[k] != None:
            if pad.getmaxyx()[0] == (row + scroll):
                # Screen full :/
                break
            try:
                pad.addstr(row, 0, get_diffline(k, curr_irq[k], old_irq[k], iv_start[k],
                           interval))
                row += 1
            except Exception as e:
                print("ERROR: %s" % e)

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

    fstr = line_format % (curr_irqline[len(curr_irqline)-1], irq, str, itot,
                          stot)

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
            if core_irqs != 'interrupts' and '-edge' not in core_irqs and \
               '-fasteoi' not in core_irqs:
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

def reset_term():
    curses.nocbreak()
    scr.keypad(0)
    curses.echo()
    curses.endwin()

def get_cpu_count():
    cpu_count = 0
    f = open('/proc/cpuinfo', 'r')
    for l in f.readlines():
        if len(l) > 4:
            key,value = l.split(':',2)
            if key.strip() == 'processor':
                cpu_count += 1
    return cpu_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Displays IRQ usage')
    parser.add_argument('--interval','-i', help="refresh interval", nargs=1,
                        type=float, default=[1])
    parser.add_argument('--match','-m', help="match IRQ name", nargs=1,
                        type=str, default='IR-')
    args = parser.parse_args()
    if len(args.interval) == 1:
        interval = float(args.interval[0])
    if len(args.match) == 1:
        match = args.match[0]
    try:
        scr = curses.initscr()
        y,x = scr.getmaxyx()
        curses.curs_set(0)
        scr.keypad(1)
        sys.exit(main())
    except KeyboardInterrupt:
        reset_term()
    except:
        reset_term()
        raise
