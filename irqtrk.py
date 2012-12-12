#!/usr/bin/python
import re
import sys
from time import sleep
import sys
import optparse
import curses
from datetime import datetime

DESCRIPTION = """Displays IRQ usage

Symbols:
 + Current interrupt
 # Old interrupt (there has been interrupts)
 - No interrupts detected
"""

class NoMatchingIRQsException(Exception):
    pass

LINE_FORMAT = '[%13s | %03s] %s [%10i | %5i]'
HEAD_FORMAT = '[%13s | %03s] %s [%10s | %5s]'

class IRQtrk(object):
    def __init__(self, match='-', interval=1.0):
        self.match = re.compile(match)
        self.interval = float(interval)
        self.scr = None
        self.pad = None
        self.hpad = None
        self.y = None
        self.x = None
        self.loops = 0
        self.time = datetime.now()
        self.old_time = datetime.now()
        self.irqs_start = None
        self.curr_irqs = {}
        self._get_irqs()
        self.irqs_start = self.curr_irqs.copy()
        self.old_irqs = self.curr_irqs.copy()
        self.irq_count = len(self.irqs_start)
        self.cpu_count = None
        self.cpu_count = self._get_cpu_count()
        # space between cpus
        self.spacing = 2
        self.scroll = 0
        self.center = ''
        self._init_screen()

    def _init_screen(self):
        self.scr = curses.initscr()
        self.y, self.x = self.scr.getmaxyx()
        # hide cursor
        curses.curs_set(0)
        self.scr.keypad(1)
        curses.noecho()
        # instant key input
        curses.cbreak()
        self.hpad = curses.newpad(1, self.x)
        self.pad = curses.newpad(self.irq_count + 7, self.x)
        # refresh every interval seconds
        self._fit_size()

    def _fit_size(self):
        """
        Fit to current window size
        """
        ny, nx = self.scr.getmaxyx()
        if ny != self.y or nx != self.x:
            # window resized
            self.scr.clear()
            self.y = ny
            self.x = nx
            self.pad.clear()
            self.pad.resize(self.y,self.x)

        if (self.cpu_count * 2 + 43) > self.x:
            self.spacing = 1
            self.center = '+/#/-'
        else:
            self.spacing = 2
            self.center = '+ = Current, # = Old, - = No'
        # ugly center placement, format available in Python >= 2.7
        for i in range((self.cpu_count * self.spacing) - len(self.center)):
            if (i % 2) == 0:
                self.center += ' '
            else:
                self.center = ' ' + self.center

    def _get_irqs(self):
        """
        Get IRQs
        """
        #irqs = {}
        try:
            irqfile = open('/proc/interrupts', 'r')
        except IOError:
            raise
        lines = irqfile.readlines()

        for line in lines:
            if len(line) > 2:
                self._parse_irqline(line)
        irqfile.close()

    def _get_cpu_count(self):
        """Get number of CPUs"""
        if not self.cpu_count:
            self.cpu_count = 0
            f = open('/proc/cpuinfo', 'r')
            for l in f.readlines():
                if len(l) > 4:
                    key,value = l.split(':',2)
                    if key.strip() == 'processor':
                        self.cpu_count += 1
        return self.cpu_count

    def _refresh_screen(self):
        row = 0
        #print header
        keys = self.curr_irqs.keys()
        self.pad.refresh(self.scroll, 0, 1, 0, self.y-1, self.x-1)
        for k in sorted(keys):
            if self.old_irqs[k] != None:
                try:
                    self.pad.addstr(row, 0, self._get_diffline(k))
                    row += 1
                except Exception as e:
                    print("ERROR: %s" % e)
                    raise
        self.hpad.addstr(0, 0, HEAD_FORMAT % ('name', 'IRQ', 
                                self.center, 'Interrupts', '1/sec'))
        self.hpad.refresh(0, 0, 0, 0, 1, self.x-1)
        self.pad.refresh(self.scroll, 0, 1, 0, self.y-1, self.x-1)
        # TODO: irqs per cpu here

    def _get_diffline(self, k):
        retval = ''
        itot = 0
        for i in range(0,len(self.curr_irqs[k])-1):
            ind = None
            
            diff_to_begin = int(self.curr_irqs[k][i])-int(self.irqs_start[k][i])
            
            if self.curr_irqs[k][i] != self.old_irqs[k][i]:
                ind = '+'
            elif diff_to_begin != 0:
                ind = '#'
            else:
                ind = '-'
            retval += " "*(self.spacing - 1) + str(ind)
            
            itot += diff_to_begin

        stot=0
        for i in range(0,len(self.curr_irqs[k])-1):
            diff_to_old = int(self.curr_irqs[k][i])-int(self.old_irqs[k][i])
            stot += diff_to_old

            time = self.time - self.old_time
            time = time.seconds + (float(time.microseconds) / 1000000)
            stot = int((stot / time)+ .5)
        name = self.curr_irqs[k][len(self.curr_irqs[k])-1][0:12]
        if stot > 100000:
            stot = 0
        return LINE_FORMAT % (name, k, retval, itot, stot)

    def _parse_irqline(self, line):
        line = line.strip()
        if self.match.search(line) == None:
            return
        data = line.split(':',2)
        if len(data) < 2:
            return
        irq = data[0]
        irqdata = data[1].strip()
        irq_per_core = []
        pattern = re.compile(r'\s+')
        irqdata_array = re.sub(pattern, ' ', irqdata).split(' ')
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
        
        # add irq name as last item
        try:
            irq = int(irq)
            irq_per_core.append(' '.join(name))
        except:
            irq_per_core.append('')
        if len(irq_per_core) < 3:
            return
        self.curr_irqs[irq] = irq_per_core

    def loop(self):
        self.scr.timeout(int(interval * 60))
        while True:
            self.loops += 1
            # update self.curr_irqs
            self.time = datetime.now()
            self._get_irqs()
            self._fit_size()
            self._refresh_screen()
            self.old_irqs = self.curr_irqs
            self.curr_irqs = {}
            self.old_time = self.time
            # Sleep
            g = 0
            while True:
                c = self.scr.getch()
                if c == curses.KEY_UP:
                    if self.scroll > 0:
                        self.scroll -= 1
                    break
                elif c == curses.KEY_DOWN:
                    if self.scroll <= (self.irq_count - self.y):
                        self.scroll += 1
                    break
                g += 1
                if g > 19:
                    break

def reset_term():
    try:
        curses.nocbreak()
        curses.echo()
        curses.endwin()
    except:
        pass

      
if __name__ == '__main__':
    parser = optparse.OptionParser(description=DESCRIPTION)
    parser.add_option('--interval','-i', help="refresh interval",
                        type=float, default=float(1),dest='interval')
    parser.add_option('--match','-m', help="match IRQ name",
                        type=str, default='-', dest='match')
    args, options = parser.parse_args()
    try:
        interval = float(args.interval)
    except:
        print('Invalid value given to -i option')
        sys.exit(1)
    match='-'
    if args.match:
        match = args.match
    try:
        c = IRQtrk(match, interval)
        sys.exit(c.loop())
    except NoMatchingIRQsException:
        print("Matching irqs not found")
        sys.exit(1)
    except KeyboardInterrupt:
        reset_term()
    except Exception as e:
        reset_term()
        raise