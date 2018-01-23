#!/usr/bin/perl -w
use strict;
use warnings;

my $command = "ifconfig eth1 | awk \'/ether/ { print \$2 } \'";
my $command1 = "ifconfig eth2 | awk \'/ether/ { print \$2 } \'";
my $output = qx/$command/;
my $count = 0;
while (length($output) < 1)
    {
    sleep(20);
    if ($count++ == 10)
        {
        last;
        }
    $output = qx/$command/;
    }
print "$output\n";

my $command2 = "ip a | awk \'/eth2/ { print \$1 }\'";
if(length(qx/$command2/) == 0)
	{ exit; }

$output = qx/$command1/;
if (system("ifconfig eth2") == 0)
    {
    exit;
    }
while (length($output) < 1)
    {
    sleep(20);
    if ($count++ == 10)
        {
        last;
        }
    $output = qx/$command1/;
    }
print "$output\n";
