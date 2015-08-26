import math
import numpy
import re
import StringIO

# Module to translate from ELEGANT to Tracy-2,3 lattice.


def marker(line, tokens):
    return  '%s: Marker;' % (tokens[0])

def marker_twiss(line, tokens):
    return marker(line, tokens) + ' { twiss }'

def marker_charge(line, tokens):
    return marker(line, tokens) + ' { %s }' % (line)

def marker_watch(line, tokens):
    return marker(line, tokens) + ' { watch }'

def marker_ematrix(line, tokens):
    return marker(line, tokens) + ' { ematrix }'

def drift(line, tokens):
    loc_l = tokens.index('l')
    return '%s: Drift, L = %s;' % (tokens[0], get_arg(tokens[loc_l+1]))

def rcol(line, tokens):
    return drift(line, tokens) + ' { rcol }'

def bend(line, tokens):
    loc_l = tokens.index('l')
    loc_phi = tokens.index('angle')
    loc_e1 = get_index(tokens, 'e1')
    loc_e2 = get_index(tokens, 'e2')
    loc_k = get_index(tokens, 'k')
    str = '%s: Bending, L = %s, T = %s' % \
        (tokens[0], get_arg(tokens[loc_l+1]), get_arg(tokens[loc_phi+1]))
    if loc_e1: str += ', T1 = %s' % (get_arg(tokens[loc_e1+1]))
    if loc_e2: str += ', T2 = %s' % (get_arg(tokens[loc_e2+1]))
    if loc_k:  str += ', K = %s' % (get_arg(tokens[loc_k+1]))
    str += ', N = Nbend, Method = 4;'
    return str

def quad(line, tokens):
    loc_l = tokens.index('l')
    loc_k = tokens.index('k1')
    str = '%s: Quadrupole, L = %s, K = %s, N = Nquad, Method = 4;' % \
        (tokens[0], get_arg(tokens[loc_l+1]),
         get_arg(tokens[loc_k+1]))
    return str

def sext(line, tokens):
    loc_l = tokens.index('l')
    loc_k = tokens.index('k2')
    str = '%s: Sextupole, L = %s, K = %s, N = Nsext, Method = 4;' % \
        (tokens[0], get_arg(tokens[loc_l+1]),
         get_arg(tokens[loc_k+1]))
    return str

def cavity(line, tokens):
    loc_l = tokens.index('l')
    loc_f = tokens.index('freq')
    loc_v = tokens.index('volt')
    loc_phi = tokens.index('phase')
    cav_name = tokens[0]+'_c'
    str = '%s: Cavity, Frequency = %s, Voltage = %s' % \
        (cav_name, get_arg(tokens[loc_f+1]), get_arg(tokens[loc_v+1]))
    if loc_phi: str += ', phi = %s' % (get_arg(tokens[loc_phi+1]))
    str += ';\n'
    drift_name = tokens[0]+'_d'
    str += '%s: Drift, L = %s;\n' % \
        (drift_name, get_arg(tokens[loc_l+1])+'/2.0')
    str += '%s: %s, %s, %s;' % \
        (tokens[0], drift_name, cav_name, drift_name)
    return str

def line(line, tokens):
    n_elem = 10 # No of elements per line.
    n = len(tokens)
    tokens[2] = tokens[2].strip('(')
    tokens[n-1] = tokens[n-1].strip(')')
    str = '%s: ' % (tokens[0])
    if n >= n_elem: str += '\n  '
    for k in range(2, n):
        if (k-1) % (n_elem+1) == 0: str += '\n  '
        if k < n-1:
            str += '%s, ' % (tokens[k])
        else:
            str += '%s;' % (tokens[k])
    return str


# Elegant -> Tracy-2,3 dictionary.
ele2tracy = {
    'charge'    : marker_charge,
    'mark'      : marker,
    'watch'     : marker_watch,
    'ematrix'   : marker_ematrix,
    'twiss'     : marker_twiss,
    'drif'      : drift,
    'drift'     : drift,
    'csrdrif'   : drift,
    'rcol'      : drift,
    'csrcsbend' : bend,
    'quad'      : quad,
    'sext'      : sext,
    'rfca'      : cavity,
    'line'      : line
    }


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass


def parse_rpnc(stack):
    # Reverse Polish Notation calculator.
    arg = stack.pop()
    if arg in '+-*/':
        op = arg
        arg = parse_rpnc(stack)
        if op == '*' and is_number(arg) and float(arg) < 0.0:
            return parse_rpnc(stack) + (' %s (%s)' % (op, arg))
        else:
            return parse_rpnc(stack) + (' %s %s' % (op, arg))
    else:
        return ('%s' % (arg))


def parse_decl(decl):
    stack = (decl.strip('%')).split()
    lhs = stack.pop()
    op = stack.pop()
    return ('%s = ' % (lhs)) + parse_rpnc(stack)


def get_index(tokens, token):
    return tokens.index(token) if token in tokens else None


def get_arg(str):
    if str.find('"') == -1:
        arg = str
    else:
        arg = parse_rpnc((str.strip('"')).split())
    return arg


def parse_definition(line, tokens):
    n_elem = 10; # No of elements per line.

    for k in range(len(tokens)):
        # Remove white space; unless a string.
        if not tokens[k].startswith('"'):
            tokens[k] = re.sub('[\s]', '', tokens[k])
    return ele2tracy[tokens[1]](line, tokens)


def parse_line(line, outf):
    line_lc = line.lower()
    if not line_lc.rstrip():
        # Blank line.
        outf.write('\n')
    elif line_lc.startswith('!'):
        # Comment.
        outf.write('{ %s }\n' % (line.strip('!')))
    elif line_lc.startswith('%'):
        # Declaration.
        outf.write('%s;\n' % (parse_decl(line_lc.strip('%'))))
    else:
        tokens = re.split(r'[,:=]', line_lc)
        if line_lc.find(':') != -1:
            # Definition.
            outf.write('%s\n' % (parse_definition(line_lc, tokens)))


def prt_decl(outf):
    outf.write('define lattice; ringtype = 1;\n')
    outf.write('\n')
    outf.write('Energy = 3.0;\n')
    outf.write('\n')
    outf.write('dP = 1e-8; CODeps = 1e-14;\n')
    outf.write('\n')
    outf.write('Meth = 4; Nbend = 4; Nquad = 4; Nsext = 2;\n')
    outf.write('\n')
    outf.write('pi = 4.0*arctan(1.0); c0 = 2.99792458e8;\n')
    outf.write('\n')


def transl_file(file_name):
    str = file_name.split('.')[0]+'.lat'
    inf = open(file_name, 'r')
    outf = open(str, 'w')
    prt_decl(outf)
    line = inf.readline()
    while line:
        line = line.strip('\r\n')
        while line.endswith('&'):
            # Line
            line = line.strip('&')
            line += (inf.readline()).strip('\r\n')
        parse_line(line, outf)
        line = inf.readline()
    outf.write('\n')
    outf.write('cell: ring, symmetry = 1;\n')
    outf.write('\n')
    outf.write('end;\n')


home_dir = '/home/bengtsson/vladimir/'

transl_file(home_dir+'lattice2p0_v1_20150522_2.lte')