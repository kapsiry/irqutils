#!/usr/bin/env python
#encoding: utf-8
"""
IRQ balancer

Copyright Kapsi Internet-käyttäjät ry

requirements:
* python-argparse
"""

USAGE = """
Usage: irqbalance.py [-h|--help] [-r|--really]
"""

CPUS = {}
DEVICES = {}

import logging
import argparse
import sys
import os

logger = logging.getLogger()

logger.setLevel(logging.DEBUG)

class CPU(object):
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        self.cores = []

    @property
    def interrupts(self):
        i = 0
        for core in self.cores:
            i += core.interrupts
        return i

    @property
    def devices(self):
        i = []
        for core in self.cores:
            for device in core.devices:
                i.append(device)
        return i

    def __str__(self):
        return "CPU %s" % (self.cpu_id,)

    def __repr__(self):
        return self.__str__()

class CORE(object):
    def __init__(self, core_id, cpu_id, local_id):
        self.core_id = core_id
        self.cpu_id = cpu_id
        self.local_id = local_id
        self.hex_mask = hex(2**core_id)[2:]
        self.interrupts = 0
        self.devices = []

    def add_interrupt(self):
        self.interrupts += 1

    def __str__(self):
        return "CORE %s on CPU %s" % (self.local_id, self.cpu_id)

    def __unicode__(self):
        return unicode(self.__str__())

    def __repr__(self):
        return self.__str__()

class IRQqueue(object):
    def __init__(self, num, device):
        self.irq = num
        self.device = device

    def __str__(self):
        return "Interrupt %s for %s" % (self.irq, self.device)

    def __repr__(self):
        return self.__str__()


def get_irq(match):
    """Get interrupts"""
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


def main(really=False, match='IR-'):
    try:
        cpuinfo = open('/proc/cpuinfo', 'r')
    except IOError:
        self.error('Cannot open /proc/cpuinfo')
    core_id = None
    cpu_id = None
    local_id = None
    for line in cpuinfo.readlines():
        if len(line) < 3:
            # new core
            if cpu_id != None and core_id != None:
                if cpu_id not in CPUS:
                    CPUS[cpu_id] = CPU(cpu_id)
                CPUS[cpu_id].cores.append(CORE(core_id, cpu_id,local_id))
            cpu_id = None
            core_id = None
            local_id = None
        else:
            try:
                key, value = line.split(':')
            except:
                continue
            key = key.strip()
            value = value.strip()
            if key == 'processor':
                core_id = int(value)
            elif key == 'physical id':
                cpu_id = value
            elif key == 'core id':
                local_id = value
    cpuinfo.close()
    logging.debug("%s" % CPUS)
    irqs = get_irq(match=match)
    for irq in irqs:
        name = irqs[irq][-1].split('-')[0]
        if name not in DEVICES:
            DEVICES[name] = []
        DEVICES[name].append(IRQqueue(irq, irqs[irq][-1].strip()))
    logging.debug("%s" % DEVICES)
    map_interrupts()
    for cpu_id in CPUS:
        logging.info("CPU %s interrupts %s" % (cpu_id, CPUS[cpu_id].interrupts))

    if really:
        alter_irq()

def map_interrupts(noob=True):
    for dev_name in DEVICES:
        dev = DEVICES[dev_name]
        cpu = CPUS[sorted(CPUS, key=lambda x: CPUS[x].interrupts)[0]]
        logging.info("DEVICE %(dev)s TO CPU %(cpu)s" % {'dev' : dev_name,
                                                        'cpu': cpu})
        for irqqueue in sorted(dev, key=lambda x: x.irq):
            # map to core
            # select core
            core = sorted(cpu.cores, key=lambda x: x.interrupts)[0]
            core.add_interrupt()
            core.devices.append(irqqueue)
            logging.debug("IRQ %s TO CORE %s" % (irqqueue.irq, core))

def alter_irq():
    for cpu in CPUS:
        for core in CPUS[cpu].cores:
            for device in core.devices:
                try:
                    f = open("/proc/irq/%s/smp_affinity" % device.irq, "w")
                    f.write(core.hex_mask)
                    f.close()
                except IOError:
                    logger.error(
                            "Can't write '%s' to /proc/irq/%s/smp_affinity" % (
                                                      core.hex_mask,device.irq))

if __name__ == '__main__':
    if not sys.platform.startswith('linux'):
        print("This script works only on Linux system!")
        sys.exit(1)
    parser = argparse.ArgumentParser(
                    description='Parse and assing IRQs on NUMA enabled system')
    parser.add_argument('--really', help='Really do changes?',
                        action='store_true')
    parser.add_argument('--debug', help='Debug', action='store_true')
    parser.add_argument('--match','-m', help="match IRQ name", nargs=1,
                        type=str, default=['IR-'])
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
    if args.really and os.getuid() != 0:
        print("This need's root privileges!")
        sys.exit(1)
    main(really=args.really, match=args.match[0])
