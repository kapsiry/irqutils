#!/usr/bin/python
import re
import sys
from time import sleep
import sys
import argparse
import curses

line_format = '[%13s | %03s] %s [%10i | %5i]'
head_format = '[%13s | %03s] %s [%10s | %5s]'

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
        ny, nx = scr.getmaxyx()
        if ny != y or nx != x:
            # screen resized
            scr.clear()
            print_header()
            y = ny
            x = nx
            pad.clear()
            pad.resize(y,x)
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
    y,x = scr.getmaxyx()
    center = '+ = Current, # = Old, - = No'
    if (cpus * 2 + 43 ) > x:
        spacing = 1
    else:
        spacing = 2
    if cpus < 15 or spacing == 1:
        center = '+/#/-'
    for i in range((cpus * spacing) - len(center)):
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
            try:
                pad.addstr(row, 0, get_diffline(k, curr_irq[k], old_irq[k], iv_start[k],
                           interval))
                row += 1
            except Exception as e:
                print("ERROR: %s" % e)

def get_diffline(irq, curr_irqline, old_irqline, iv_start, interval):
    str = ""
    y,x = scr.getmaxyx()

    itot=0
    if ((len(curr_irqline) - 1)*2 + 43) > x:
        spacing = 0
    else:
        spacing = 1
    for i in range(0,len(curr_irqline)-1):
        ind = None

        diff_to_begin = int(curr_irqline[i])-int(iv_start[i])

        if curr_irqline[i] != old_irqline[i]:
            ind = '+'
        elif diff_to_begin != 0:
            ind = '#'
        else:
            ind = '-'
        str = str + " "*spacing + "%s" % (ind)

        itot += diff_to_begin

    stot=0

    for i in range(0,len(curr_irqline)-1):

        diff_to_old = int(curr_irqline[i])-int(old_irqline[i])
        stot += diff_to_old

    stot = stot / interval

    fstr = line_format % (curr_irqline[len(curr_irqline)-1][0:12], irq, str, itot,
                          stot)

    return fstr

def get_irq():
    irqfile = open('/proc/interrupts', 'r')
    lines = irqfile.readlines()

    irqs = {}

    for line in lines:
        if len(line) > 2:
            irqline_res = parse_irqline(line)
            if irqline_res:
                irqs[irqline_res[0]] = irqline_res[1]

    return irqs

def parse_irqline(line):
    line = line.strip()

    if match.search(line) == None:
        return

    data = line.split(':',2)
    if len(data) < 2:
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
    parser = argparse.ArgumentParser(description=
        """Displays IRQ usage

Symbols:
 + Current interrupt
 # Old interrupt (there has been interrupts)
 - No interrupts detected""",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--interval','-i', help="refresh interval", nargs=1,
                        type=float, default=[1])
    parser.add_argument('--match','-m', help="match IRQ name", nargs=1,
                        type=str, default='IR-')
    args = parser.parse_args()
    if len(args.interval) == 1:
        interval = float(args.interval[0])
    if len(args.match) == 1:
        match = args.match[0]
    match = re.compile(match)
    try:
        if len(get_irq()) == 0:
            print("Matching irqs not found")
            sys.exit(1)
        scr = curses.initscr()
        y,x = scr.getmaxyx()
        curses.curs_set(0)
        scr.keypad(1)
        sys.exit(main())
    except KeyboardInterrupt:
        reset_term()
    except Exception:
        reset_term()
        raise
