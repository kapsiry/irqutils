#!/usr/bin/python
import re
import sys
from time import sleep

def main():
	interval=0.1

	sys.stderr.write("\x1b[2J\x1b[H")

	iv_start = get_irq()
	old_irq = iv_start.copy()

	sleep(interval)

	while True:
		curr_irq = get_irq()
		sys.stderr.write("\x1b[H")
		print_irqdiff(curr_irq, old_irq, iv_start)
		old_irq = curr_irq
		sleep(0.3)

def print_irqdiff(curr_irq, old_irq, iv_start):
	keys = curr_irq.keys()
	for k in sorted(keys):
		if old_irq[k] != None:
			print(get_diffline(k, curr_irq[k], old_irq[k], iv_start[k]))

def get_diffline(irq, curr_irqline, old_irqline, iv_start):
	str = ""

	itot=0

	for i in range(0,len(curr_irqline)-2):
		ind = None

		diff_to_begin = int(curr_irqline[i])-int(iv_start[i])

		if curr_irqline[i] != old_irqline[i]: ind = '!'
		elif diff_to_begin != 0: ind = '+'
		else: ind = '-'
		
		str = str + " %s" % (ind) 

		itot += diff_to_begin

	fstr = '[iv %12s @ irq %03i] %s [ti=%10i]' % (curr_irqline[len(curr_irqline)-1], int(irq), str, itot)

	return fstr

#def get_irq(match='TxRx'):
def get_irq(match='eth2'):
	irqfile = open('/proc/interrupts', 'r')
	lines = irqfile.readlines()
	
	irqs = {}
	
	for line in lines:
		if len(line) > 2:
			irqline_res = parse_irqline(line, match)
			if irqline_res: irqs[irqline_res[0]] = irqline_res[1]

	return irqs

def parse_irqline(line, match):
	line = line.strip()

	if match not in line: return

	data = line.split(':')
	if len(data) != 2: return

	irq = data[0]
	irqdata = data[1]

	irq_per_core = []

	pattern = re.compile(r'\s+')
	irqdata_array = re.sub(pattern, ' ', irqdata.strip()).split(' ')
	for core_irqs in irqdata_array:
		irq_per_core.append(core_irqs)

	return [irq, irq_per_core]

if __name__ == "__main__":
	try:
		sys.exit(main())
	except KeyboardInterrupt:
		pass
