#!/usr/bin/python

#############################################################################
#                                                                           #
# This script was initially developed by Infoxchange for internal use       #
# and has kindly been made available to the Open Source community for       #
# redistribution and further development under the terms of the             #
# GNU General Public License v2: http://www.gnu.org/licenses/gpl.html       #
# Copyright 2015 Infoxchange                                                #
#                                                                           #
#############################################################################
#                                                                           #
# This script is supplied 'as-is', in the hope that it will be useful, but  #
# neither Infoxchange nor the authors make any warranties or guarantees     #
# as to its correct operation, including its intended function.             #
#                                                                           #
# Or in other words:                                                        #
#       Test it yourself, and make sure it works for YOU.                   #
#                                                                           #
#############################################################################
# Author: George Hansper                     e-mail:  george@hansper.id.au  #
#############################################################################


import sys, getopt, time, socket
import os

BUFFER_SIZE = 4096
host_name = '127.0.0.1'
tcp_port = 1337
unix_socket = ''
t_timeout = 30.0
t_warn = 5
t_crit = 15
verbose = 0
version = '$Id:$'

from_addr = 'nagios@nagios.greylist.check'
to_addr   = 'nagios@nagios.greylist.check'
# This IP should NEVER appear in real life, so it's good for this check
# 192.0.2.0/24 = TEST-NET-1 - See: RFC 5737 "IPv4 Address Blocks Reserved for Documentation"
client_ip = '192.0.2.1'
helo_name = 'nagios.greylist.check'

policy_request_template = '''request=smtpd_access_policy
client_name=nagios.greylist.test
helo_name=%s
sender=%s
recipient=%s
client_address=%s

'''

perf_message=''
result_message=''
result_full=''

def print_v(msg):
  global verbose
  if verbose:
    sys.stderr.write(msg+"\n")

def usage():
        global host_name, tcp_port, verbose, t_timeout
        global from_addr, to_addr, client_ip, helo_name
        global t_warn, t_crit
        print('Usage: ' + sys.argv[0] + " [-H host] [-p port] [-u /path_to/socket] [-T timeout] [-w time_s] [-c time_s] [-v] [-V]")
        print("""
        -H, --host     ... connect to this host (name or IP address) default: %s
                           also accepts host:port syntax
        -p, --port     ... connect to this port on host (name or IP address) default: %s
        -u, --unix     ... connect to the unix socket at this path (default is to use TCP instead)
        -T, --timeout  ... connect within this many seconds (floating point), default: %.1f
        -w, --warn     ... warning if query exceeds this many seconds (floating point), default: %.1f
        -c, --crit     ... critical if query exceeds this many seconds (floating point), default: %.1f
        -f, --from     ... use this as the sender, default: %s
        -i, --ip       ... use this as the client_address, default: %s
        -t, --to       ... use this as the recipient, default: %s
        -e, --helo     ... use this as the helo_name, default: %s

        -v, --verbose  ... verbose messages, print full response
        -h, --help     ... print this help message

""" % ( host_name, tcp_port, t_timeout, t_warn, t_crit, from_addr, client_ip, to_addr, helo_name ) )

def command_args(argv):
  global host_name, tcp_port, unix_socket, verbose, t_timeout
  global from_addr, to_addr, client_ip, helo_name
  global t_warn, t_crit
  global version
  try:
    opts, args = getopt.getopt(argv, 'H:p:u:T:w:c:f:i:e:t:vhV', ['host=', 'port=', 'unix=', 'timeout=', 'warn=', 'crit=', 'from=', 'ip=', 'to=', 'helo=', 'verbose', 'version', 'help'])
  except getopt.GetoptError:
    usage()
    sys.exit(3)
  for opt, arg in opts:
    #arg = arg.rstrip('%')
    if opt in ('-H', '--host'):
      host_port = arg.split(':',2)
      host_name = host_port[0]
      if len(host_port)>1:
        tcp_port = int(host_port[1])
    elif opt in ('-p', '--port'):
      tcp_port = int(arg)
    elif opt in ('-u', '--unix'):
      unix_socket = arg
    elif opt in ('-T', '--timeout'):
      t_timeout = float(arg)
    elif opt in ('-w', '--warn'):
      t_warn = float(arg)
    elif opt in ('-c', '--crit'):
      t_crit = float(arg)
    elif opt in ('-f', '--from'):
      from_addr = arg
    elif opt in ('-t', '--to'):
      to_addr = arg
    elif opt in ('-i', '--ip'):
      client_ip = arg
    elif opt in ('-e', '--helo'):
      helo_name = arg
    elif opt in ('-h', '--help'):
      usage()
      sys.exit(1)
    elif opt in ('-V', '--version'):
      print(version)
      sys.exit(1)
    elif opt in ('-v', '--verbose'):
      verbose = 1

def connect_to_socket(unix_socket,data,timeout):
    try:
      s = socket.socket(socket.AF_UNIX)
      #s = socket.create_connection(unix_socket, int(timeout) )
      s.connect(unix_socket)
      s.settimeout(timeout)
      s.setblocking(1)
    except IOError as ioerr:
      return (2, "Error connecting to unix socket: %s - %s" % (unix_socket, ioerr), '')
    try:
      s.settimeout(timeout)
      # Python 2.x/Python 3 incompatibility
      if sys.version_info < (3, 0):
        s.sendall(bytes(data))
      else:
        s.sendall(bytes(data,'UTF-8'))
      #s.shutdown(socket.SHUT_WR)
    except IOError as ioerr:
      return (2, "Error sending to unix socket %s - %s" % (unix_socket, ioerr), '')
    try:
      # Python 2.x/Python 3 incompatibility
      if sys.version_info < (3, 0):
        result_full = s.recv(BUFFER_SIZE).strip()
      else:
        result_full = s.recv(BUFFER_SIZE).decode(encoding='UTF-8').strip()
      s.shutdown(socket.SHUT_RDWR)
    except IOError as ioerr:
      return (2, "Error receiving from unix socket %s - %s" % (unix_socket, ioerr), '')
    return(0,'',result_full)

def connect_to_tcp_port(host,tcp_port,data,timeout):
    try:
      s = socket.create_connection((host, tcp_port), int(timeout ))
      s.settimeout(timeout)
      s.setblocking(1)
    except IOError as ioerr:
      return (2, "Error connecting to server: %s:%d - %s" % (host, tcp_port, ioerr), '')
    try:
      s.settimeout(timeout)
      # Python 2.x/Python 3 incompatibility
      if sys.version_info < (3, 0):
        s.sendall(bytes(data))
      else:
        s.sendall(bytes(data,'UTF-8'))
      #s.shutdown(socket.SHUT_WR)
    except IOError as ioerr:
      return (2, "Error sending to tcp connection %s:%s - %s" % (host, tcp_port, ioerr) ,'')
    try:
      # Python 2.x/Python 3 incompatibility
      if sys.version_info < (3, 0):
        result_full = s.recv(BUFFER_SIZE).strip()
      else:
        result_full = s.recv(BUFFER_SIZE).decode(encoding='UTF-8').strip()
      s.shutdown(socket.SHUT_RDWR)
    except IOError as ioerr:
      return (2, "Error receiving from tcp connection %s:%s - %s" % (host, tcp_port, ioerr) ,'')
    return(0,'',result_full)

def check_greylist_result(result_full):
    if len(result_full) > 63:
      result = result_full[:60] + '...'
    else:
      result = result_full
    if len(result) == 0:
      return(2, 'Empty response from greylister')
    result_list = result.split('=',2)
    if result_list[0] != 'action':
      return(2, 'Expected action=... but response was: %s' % result.splitlines()[0])
    elif result_list[1].upper().startswith('DUNNO'):
      return (0,result)
    elif result_list[1].upper().startswith('DEFER_IF_PERMIT'):
      return (1,result + ' (this warning should go away, when greylisting is over)')
    elif result_list[1].upper().startswith('PREPEND'):
      return (1,result + ' (this should change to DUNNO on the next check)')
    return (4,result + ' - unexpected action=..., exepcting DUNNO or DEFER_IF_PERMIT or PREPEND')


# Parse command line args
command_args(sys.argv[1:])

# Construct the policy query
policy_request = policy_request_template % ( helo_name, from_addr, to_addr, client_ip )
print_v(policy_request)

# Get the greytlister results
t_start = time.time()
if unix_socket == '':
  (exit_code,result_message,result_full) = connect_to_tcp_port(host_name, tcp_port, policy_request, t_timeout)
else:
  (exit_code,result_message,result_full) = connect_to_socket(unix_socket, policy_request, t_timeout)
t_result   = time.time() - t_start
perf_message = 't=%f' % t_result
 
# Check the result
if exit_code == 0:
  (exit_code,result_message) = check_greylist_result(result_full)

# Check timing
if t_result > t_crit:
  exit_code |= 2
  result_message += ', (!!) t=%0.3f > %0.3f' % ( t_result, t_crit )
elif t_result > t_warn:
  exit_code |= 1
  result_message += ', (!) t=%0.3f > %0.3f' % ( t_result, t_warn )
else:
  result_message += ', t=%0.3f' % t_result

# Write the result(s)
if exit_code == 0:
  state = 'OK'
elif exit_code == 1:
  state = 'WARNING'
elif exit_code == 2 or exit_code == 3:
  state = 'CRITICAL'
  exit_code = 2
else:
  state = 'UNKNOWN'
  exit_code = 3

print('%s: %s|%s' % ( state, result_message, perf_message ))
# Long service output - useful for debugging
print(result_full)
sys.exit(exit_code)

