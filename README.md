check_greylist.py
=================

This is a Nagios plugin, for checking the normal operation of a Postfix greylisting policy-daemon.

The Postfix mail server can use policy-deamons to accecpt, reject, or defer (greylist) e-mail.

If a policy-deamon is used, it is essential that this be working correctly, in order for Postfix to process e-mail.

### Prerequisites
* If you are running Postfix as a mail-server
    and
* If you are using a Greylister on a TCP port

Then this plugin is for you

### What it does

This script connects to the policy daemon via TCP, provides some basic (fake) information, and reads the reply.
For a greylister, only 2 responses are valid:

* DUNNO
  * accept, subject to later rules
* DEFER_IF_PERMIT
  * greylist, but only if no other policy tells Postfix to REJECT the e-mai

Since the check runs periodically, with the same data, it very quickly passes the greylisting period.
During greylisting, the check returns a warning status.

After greylisting has expired, the check should see DUNNO forever more.
A response of DUNNO indicates that the greylister is capable of allowing messages to pass greylisting.

This is not a comprehensive test of the greylister, but it is a step beyond a simple TCP connect.

#### Sample Output (normal)

```
OK: action=DUNNO, t=0.005|t=0.005287
action=DUNNO
```

#### Sample Output (while greylisted)

```
WARNING: action=DEFER_IF_PERMIT greylisted, try again later (this warning should go away, when greylisting is over), t=1.146|t=1.146290
action=DEFER_IF_PERMIT greylisted, try again later
```

### Sample config

```
define service {
  use                            generic-service          ; template name
  service_description            greylist-policyd
  hostgroup_name                 mail-servers
  check_command                  check_nrpe_1arg!check_greylist -t 60
}
```

`nrpe.cfg` config

```
# Port 1337 is used by the bley greylister
command[check_greylist]=/usr/lib/nagios/plugins/check_greylist.py -H localhost -p 1337
```

### Performance Data

This plugin measures the response time of the policyd.
This is the only performance data generated, and works well with the default PNP4Nagios template.
